import { createPublicClient, createWalletClient, http, type Hex, type Address, parseAbi, encodeFunctionData } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { anvil } from 'viem/chains';

export async function executeSkill(rpcUrl: string, privateKey: string, chainId: number = 31337): Promise<string> {
  const account = privateKeyToAccount(privateKey as Hex);
  const pub = createPublicClient({ chain: { ...anvil, id: chainId }, transport: http(rpcUrl) });
  const wallet = createWalletClient({ account, chain: { ...anvil, id: chainId }, transport: http(rpcUrl) });

  const results: Array<{ txHash: string; to: string; selector: string; success: boolean }> = [];

  // Targeting ERC20 (0x9fe46736679d2d9a65f0992f2272de9f3c7fa6e0)
  const erc20Name = encodeFunctionData({
    abi: [{ name: 'name', type: 'function', inputs: [], outputs: [{ type: 'string' }] }],
    functionName: 'name',
  });
  const erc20Symbol = encodeFunctionData({
    abi: [{ name: 'symbol', type: 'function', inputs: [], outputs: [{ type: 'string' }] }],
    functionName: 'symbol',
  });
  const erc20Decimals = encodeFunctionData({
    abi: [{ name: 'decimals', type: 'function', inputs: [], outputs: [{ type: 'uint8' }] }],
    functionName: 'decimals',
  });
  const erc20TotalSupply = encodeFunctionData({
    abi: [{ name: 'totalSupply', type: 'function', inputs: [], outputs: [{ type: 'uint256' }] }],
    functionName: 'totalSupply',
  });

  const erc20Tx1 = await wallet.sendTransaction({
    to: '0x9fe46736679d2d9a65f0992f2272de9f3c7fa6e0',
    data: erc20Name,
  });
  const erc20Tx2 = await wallet.sendTransaction({
    to: '0x9fe46736679d2d9a65f0992f2272de9f3c7fa6e0',
    data: erc20Symbol,
  });
  const erc20Tx3 = await wallet.sendTransaction({
    to: '0x9fe46736679d2d9a65f0992f2272de9f3c7fa6e0',
    data: erc20Decimals,
  });
  const erc20Tx4 = await wallet.sendTransaction({
    to: '0x9fe46736679d2d9a65f0992f2272de9f3c7fa6e0',
    data: erc20TotalSupply,
  });

  // Targeting WETH (0x851356ae760d987e095750cceb3bc6014560891c)
  const wethName = encodeFunctionData({
    abi: [{ name: 'name', type: 'function', inputs: [], outputs: [{ type: 'string' }] }],
    functionName: 'name',
  });
  const wethSymbol = encodeFunctionData({
    abi: [{ name: 'symbol', type: 'function', inputs: [], outputs: [{ type: 'string' }] }],
    functionName: 'symbol',
  });
  const wethDecimals = encodeFunctionData({
    abi: [{ name: 'decimals', type: 'function', inputs: [], outputs: [{ type: 'uint8' }] }],
    functionName: 'decimals',
  });
  const wethTotalSupply = encodeFunctionData({
    abi: [{ name: 'totalSupply', type: 'function', inputs: [], outputs: [{ type: 'uint256' }] }],
    functionName: 'totalSupply',
  });

  const wethTx1 = await wallet.sendTransaction({
    to: '0x851356ae760d987e095750cceb3bc6014560891c',
    data: wethName,
  });
  const wethTx2 = await wallet.sendTransaction({
    to: '0x851356ae760d987e095750cceb3bc6014560891c',
    data: wethSymbol,
  });
  const wethTx3 = await wallet.sendTransaction({
    to: '0x851356ae760d987e095750cceb3bc6014560891c',
    data: wethDecimals,
  });
  const wethTx4 = await wallet.sendTransaction({
    to: '0x851356ae760d987e095750cceb3bc6014560891c',
    data: wethTotalSupply,
  });

  // Collecting results
  const [erc20R1, erc20R2, erc20R3, erc20R4, wethR1, wethR2, wethR3, wethR4] = await Promise.all([
    pub.waitForTransactionReceipt({ hash: erc20Tx1 }),
    pub.waitForTransactionReceipt({ hash: erc20Tx2 }),
    pub.waitForTransactionReceipt({ hash: erc20Tx3 }),
    pub.waitForTransactionReceipt({ hash: erc20Tx4 }),
    pub.waitForTransactionReceipt({ hash: wethTx1 }),
    pub.waitForTransactionReceipt({ hash: wethTx2 }),
    pub.waitForTransactionReceipt({ hash: wethTx3 }),
    pub.waitForTransactionReceipt({ hash: wethTx4 }),
  ]);

  results.push({
    txHash: erc20Tx1,
    to: '0x9fe46736679d2d9a65f0992f2272de9f3c7fa6e0',
    selector: erc20Name.slice(0, 10),
    success: erc20R1.status === 'success',
  });
  results.push({
    txHash: erc20Tx2,
    to: '0x9fe46736679d2d9a65f0992f2272de9f3c7fa6e0',
    selector: erc20Symbol.slice(0, 10),
    success: erc20R2.status === 'success',
  });
  results.push({
    txHash: erc20Tx3,
    to: '0x9fe46736679d2d9a65f0992f2272de9f3c7fa6e0',
    selector: erc20Decimals.slice(0, 10),
    success: erc20R3.status === 'success',
  });
  results.push({
    txHash: erc20Tx4,
    to: '0x9fe46736679d2d9a65f0992f2272de9f3c7fa6e0',
    selector: erc20TotalSupply.slice(0, 10),
    success: erc20R4.status === 'success',
  });

  results.push({
    txHash: wethTx1,
    to: '0x851356ae760d987e095750cceb3bc6014560891c',
    selector: wethName.slice(0, 10),
    success: wethR1.status === 'success',
  });
  results.push({
    txHash: wethTx2,
    to: '0x851356ae760d987e095750cceb3bc6014560891c',
    selector: wethSymbol.slice(0, 10),
    success: wethR2.status === 'success',
  });
  results.push({
    txHash: wethTx3,
    to: '0x851356ae760d987e095750cceb3bc6014560891c',
    selector: wethDecimals.slice(0, 10),
    success: wethR3.status === 'success',
  });
  results.push({
    txHash: wethTx4,
    to: '0x851356ae760d987e095750cceb3bc6014560891c',
    selector: wethTotalSupply.slice(0, 10),
    success: wethR4.status === 'success',
  });

  return JSON.stringify({ results, error: null });
}