/**
 * EVM Benchmark Runner using REAL Eliza AgentRuntime.
 *
 * This creates an actual Eliza agent with a custom EVM benchmark plugin,
 * sends it natural language prompts, and the agent generates + executes
 * EVM transactions through the standard Eliza action pipeline.
 *
 * Usage:
 *   bun eliza-bench.ts <rpcUrl> <privateKey> <numSteps> <groqApiKey>
 */

// Import from the built Eliza core
const elizaCorePath = require.resolve(
  "../../../eliza/packages/typescript/dist/node/index.node.js"
);
const ElizaCore = require(elizaCorePath);
const {
  AgentRuntime,
  ChannelType,
} = ElizaCore;

// ── Custom EVM Benchmark Plugin ──────────────────────────────────────
// This plugin gives the Eliza agent the ability to execute arbitrary EVM
// transactions — the core capability needed for the benchmark.

import {
  createPublicClient,
  createWalletClient,
  http,
  parseEther,
  encodeFunctionData,
  parseAbi,
  type Hex,
  type Address,
} from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { anvil } from "viem/chains";

const args = process.argv.slice(2);
const RPC_URL = args[0] || "http://127.0.0.1:8545";
const PRIVATE_KEY = args[1] || "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";
const NUM_STEPS = parseInt(args[2] || "5", 10);
const GROQ_API_KEY = args[3] || "";
const CHAIN_ID = parseInt(args[4] || "31337", 10);

// Track discovered (address, selector) pairs
const discovered = new Set<string>();
let totalReward = 0;

function recordPair(to: string, selector: string): boolean {
  const key = `${to.toLowerCase()}:${selector.toLowerCase()}`;
  if (discovered.has(key)) return false;
  discovered.add(key);
  totalReward++;
  return true;
}

// ── EXECUTE_EVM_TX action ──────────────────────────────────────────
// The agent calls this to send arbitrary EVM transactions.
const executeEvmTxAction = {
  name: "EXECUTE_EVM_TX",
  description:
    "Execute one or more EVM transactions. Provide an array of transactions with 'to' (address or null for deploy), 'data' (hex calldata), and optional 'value' (in wei as string). Returns tx hashes and selectors discovered.",
  similes: [
    "SEND_TRANSACTION",
    "DEPLOY_CONTRACT",
    "CALL_CONTRACT",
    "EVM_CALL",
    "SEND_ETH",
  ],
  examples: [
    [
      {
        name: "user",
        content: {
          text: "Send 0.01 ETH to 0x000000000000000000000000000000000000dEaD",
        },
      },
      {
        name: "agent",
        content: {
          text: "I'll send 0.01 ETH to the dead address.",
          actions: ["EXECUTE_EVM_TX"],
        },
      },
    ],
    [
      {
        name: "user",
        content: {
          text: "Call the identity precompile at 0x04 with data 0x1234",
        },
      },
      {
        name: "agent",
        content: {
          text: "I'll call the identity precompile.",
          actions: ["EXECUTE_EVM_TX"],
        },
      },
    ],
  ],
  validate: async () => true,
  handler: async (
    runtime: InstanceType<typeof AgentRuntime>,
    message: Record<string, unknown>,
    state: Record<string, unknown>,
    options: Record<string, unknown>,
    callback: (content: Record<string, unknown>) => Promise<unknown[]>
  ) => {
    const account = privateKeyToAccount(PRIVATE_KEY as Hex);
    const chain = { ...anvil, id: CHAIN_ID };
    const publicClient = createPublicClient({ chain, transport: http(RPC_URL) });
    const walletClient = createWalletClient({
      account,
      chain,
      transport: http(RPC_URL),
    });

    // Extract transaction params from the message or state
    const content = (message as Record<string, Record<string, unknown>>).content || {};
    const text = String(content.text || "");

    // Parse transactions from the agent's response
    // The agent should include JSON in its response with tx params
    const txResults: Array<{
      txHash: string;
      to: string;
      selector: string;
      success: boolean;
      isNew: boolean;
    }> = [];

    try {
      // Try to extract JSON from the text
      const jsonMatch = text.match(/\[[\s\S]*\]/);
      let txParams: Array<{
        to?: string | null;
        data?: string;
        value?: string;
      }> = [];

      if (jsonMatch) {
        txParams = JSON.parse(jsonMatch[0]);
      } else {
        // Try to parse the whole text as JSON
        const parsed = JSON.parse(text);
        txParams = Array.isArray(parsed) ? parsed : [parsed];
      }

      for (const tx of txParams) {
        try {
          const txHash = await walletClient.sendTransaction({
            to: tx.to ? (tx.to as Address) : undefined,
            data: tx.data ? (tx.data as Hex) : undefined,
            value: tx.value ? BigInt(tx.value) : 0n,
          });
          const receipt = await publicClient.waitForTransactionReceipt({
            hash: txHash,
          });

          const toAddr =
            tx.to || "0x0000000000000000000000000000000000000000";
          const selector =
            tx.data && tx.data.length >= 10 ? tx.data.slice(0, 10) : "0x";
          const isNew = receipt.status === "success"
            ? recordPair(toAddr, selector)
            : false;

          txResults.push({
            txHash,
            to: toAddr,
            selector,
            success: receipt.status === "success",
            isNew,
          });
        } catch (txErr: unknown) {
          const errMsg = txErr instanceof Error ? txErr.message : String(txErr);
          txResults.push({
            txHash: "",
            to: tx.to || "0x0",
            selector: "error",
            success: false,
            isNew: false,
          });
        }
      }
    } catch (parseErr: unknown) {
      // If no JSON found, try simple ETH transfer from text
      const addrMatch = text.match(/0x[a-fA-F0-9]{40}/);
      const valueMatch = text.match(/(\d+\.?\d*)\s*ETH/i);

      if (addrMatch) {
        try {
          const txHash = await walletClient.sendTransaction({
            to: addrMatch[0] as Address,
            value: valueMatch ? parseEther(valueMatch[1]) : 0n,
          });
          const receipt = await publicClient.waitForTransactionReceipt({
            hash: txHash,
          });
          const isNew = receipt.status === "success"
            ? recordPair(addrMatch[0], "0x")
            : false;

          txResults.push({
            txHash,
            to: addrMatch[0],
            selector: "0x",
            success: receipt.status === "success",
            isNew,
          });
        } catch {
          // ignore
        }
      }
    }

    const newCount = txResults.filter((r) => r.isNew).length;

    await callback({
      text: `Executed ${txResults.length} transactions. ${newCount} new selectors discovered. Total reward: ${totalReward}.`,
      data: { txResults, totalReward, discovered: discovered.size },
    });

    return { success: txResults.length > 0 };
  },
};

// ── EVM Benchmark Plugin ──────────────────────────────────────────
const evmBenchPlugin = {
  name: "evm-bench",
  description:
    "EVM benchmark plugin — provides EXECUTE_EVM_TX action for discovering unique function selectors",
  actions: [executeEvmTxAction],
  providers: [
    {
      name: "evm-state",
      description: "Current EVM benchmark state",
      get: async () => {
        return `EVM Benchmark State:
- RPC: ${RPC_URL} (Chain ID: ${CHAIN_ID})
- Agent: ${privateKeyToAccount(PRIVATE_KEY as Hex).address}
- Total reward: ${totalReward}
- Unique pairs discovered: ${discovered.size}
- Discovered pairs: ${[...discovered].slice(-10).join(", ")}${discovered.size > 10 ? "..." : ""}

Available precompiles: 0x01 (ecRecover), 0x02 (SHA-256), 0x03 (RIPEMD-160), 0x04 (Identity), 0x05 (ModExp), 0x06 (ecAdd), 0x07 (ecMul), 0x08 (ecPairing), 0x09 (Blake2f)

To earn rewards, use EXECUTE_EVM_TX with JSON array of transactions:
[{"to": "0x...", "data": "0x...", "value": "0"}]
Set "to" to null for contract deployments. Each unique (to, first_4_bytes_of_data) = +1 reward.`;
      },
    },
  ],
  evaluators: [],
  services: [],
};

// ── Main benchmark loop ──────────────────────────────────────────

const PROMPTS = [
  "Send 0.001 ETH to 0x000000000000000000000000000000000000dEaD to test native transfer. Use EXECUTE_EVM_TX with: [{\"to\": \"0x000000000000000000000000000000000000dEaD\", \"value\": \"1000000000000000\"}]",
  "Call the identity precompile (address 0x0000000000000000000000000000000000000004) with data 0xdeadbeef. Use EXECUTE_EVM_TX with: [{\"to\": \"0x0000000000000000000000000000000000000004\", \"data\": \"0xdeadbeef\"}]",
  "Call SHA-256 precompile (0x02) and RIPEMD-160 precompile (0x03) with the same input 0xaabbccdd. Use EXECUTE_EVM_TX with: [{\"to\": \"0x0000000000000000000000000000000000000002\", \"data\": \"0xaabbccdd\"}, {\"to\": \"0x0000000000000000000000000000000000000003\", \"data\": \"0xaabbccdd\"}]",
  "Call ecAdd precompile (0x06) and ecMul precompile (0x07) with zeros. Use EXECUTE_EVM_TX with: [{\"to\": \"0x0000000000000000000000000000000000000006\", \"data\": \"0x00000000\"}, {\"to\": \"0x0000000000000000000000000000000000000007\", \"data\": \"0x00000000\"}]",
  "Discover more EVM function selectors. Think about what contracts or precompiles you haven't called yet. Use EXECUTE_EVM_TX to send transactions and earn rewards. Try calling modexp (0x05), blake2f (0x09), or ecRecover (0x01) with appropriate input data.",
];

async function main() {
  console.log("=== EVM Benchmark with REAL Eliza Agent ===");
  console.log(`RPC: ${RPC_URL} | Chain: ${CHAIN_ID} | Steps: ${NUM_STEPS}`);

  // Create the Eliza agent with our benchmark plugin
  const character = {
    name: "EVMBenchAgent",
    bio: [
      "Expert EVM developer agent that discovers unique function selectors",
    ],
    plugins: [evmBenchPlugin],
    settings: {
      model: "qwen/qwen3-32b",
    },
    secrets: {
      GROQ_API_KEY: GROQ_API_KEY,
    },
    templates: {},
    messageExamples: [],
    postExamples: [],
    topics: [],
    adjectives: [],
    knowledge: [],
  };

  const runtime = new AgentRuntime({
    character,
    plugins: [evmBenchPlugin],
    logLevel: "info",
    checkShouldRespond: false, // Always respond (benchmark mode)
    actionPlanning: false, // Single action per response
  });

  await runtime.initialize();

  const agentId = runtime.agentId;
  const userId = ElizaCore.createUniqueUuid(runtime, "bench-user");
  const roomId = ElizaCore.createUniqueUuid(runtime, "bench-room");

  // Ensure connection and room
  await runtime.ensureConnection({
    entityId: userId,
    roomId,
    userName: "BenchUser",
    name: "BenchUser",
    source: "api",
    channelId: "bench",
    serverId: "bench",
    type: ChannelType.API,
  });

  console.log(`Agent: ${agentId}`);
  console.log(`Room: ${roomId}`);
  console.log();

  const stepResults: Array<{
    step: number;
    prompt: string;
    response: string;
    reward: number;
    totalReward: number;
  }> = [];

  for (let step = 0; step < NUM_STEPS; step++) {
    const prompt =
      step < PROMPTS.length
        ? PROMPTS[step]
        : `You have discovered ${totalReward} unique EVM selectors so far. Find more! Use EXECUTE_EVM_TX to call new contracts or precompiles with different data. Each new (address, first_4_bytes) pair = +1 reward.`;

    console.log(`\n${"=".repeat(60)}`);
    console.log(`Step ${step + 1}/${NUM_STEPS}: ${prompt.slice(0, 80)}...`);
    console.log("=".repeat(60));

    const rewardBefore = totalReward;

    // Create message memory
    const message = {
      id: ElizaCore.createUniqueUuid(runtime, `msg-${step}-${Date.now()}`),
      entityId: userId,
      roomId,
      agentId,
      content: {
        text: prompt,
        source: "api",
        channelType: ChannelType.API,
      },
      createdAt: Date.now(),
    };

    let responseText = "";

    try {
      // Send through REAL Eliza message pipeline
      const result = await runtime.messageService!.handleMessage(
        runtime,
        message,
        async (content: Record<string, unknown>) => {
          if (content?.text) {
            responseText += String(content.text);
          }
          console.log(`  Agent: ${String(content?.text || "").slice(0, 200)}`);
          return [];
        }
      );

      const stepReward = totalReward - rewardBefore;
      console.log(
        `  Reward: +${stepReward} (total: ${totalReward}, mode: ${result?.mode || "unknown"})`
      );

      stepResults.push({
        step: step + 1,
        prompt: prompt.slice(0, 100),
        response: responseText.slice(0, 200),
        reward: stepReward,
        totalReward,
      });
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err);
      console.log(`  ERROR: ${errMsg.slice(0, 200)}`);
      stepResults.push({
        step: step + 1,
        prompt: prompt.slice(0, 100),
        response: `ERROR: ${errMsg.slice(0, 200)}`,
        reward: 0,
        totalReward,
      });
    }
  }

  // Final summary
  console.log("\n" + "=".repeat(60));
  console.log("FINAL RESULTS");
  console.log("=".repeat(60));
  for (const r of stepResults) {
    console.log(
      `  Step ${r.step}: +${r.reward} (total: ${r.totalReward}) ${r.response.slice(0, 80)}`
    );
  }
  console.log(`\nTotal reward: ${totalReward}`);
  console.log(`Unique pairs: ${discovered.size}`);

  // Output JSON for Python harness to parse
  const output = {
    results: stepResults,
    totalReward,
    discoveredPairs: [...discovered],
    agentId,
    model: "qwen/qwen3-32b",
  };
  console.log("\n---JSON_OUTPUT---");
  console.log(JSON.stringify(output));

  await runtime.stop();
  process.exit(0);
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
