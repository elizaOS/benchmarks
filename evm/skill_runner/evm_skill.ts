import { createPublicClient, createWalletClient, http, type Hex, type Address, parseAbi, encodeFunctionData } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { anvil } from 'viem/chains';
export async function executeSkill(rpcUrl: string, privateKey: string, chainId: number = 31337): Promise<string> {
  const account = privateKeyToAccount(privateKey as Hex);
  const pub = createPublicClient({ chain: { ...anvil, id: chainId }, transport: http(rpcUrl) });
  const wallet = createWalletClient({ account, chain: { ...anvil, id: chainId }, transport: http(rpcUrl) });
  const abi = parseAbi(['function mint(address to, uint256 amount) returns (bool)']);
  const data = encodeFunctionData({ abi, functionName: 'mint', args: [account.address, 1000000000000000000n] });
  const { hash } = await wallet.sendTransaction({
    to: '0xa513e6e4b8f2a923d98304ec87f64353c4d5c853',
    data: data,
  });
  const receipt = await pub.waitForTransactionReceipt({ hash });
  return JSON.stringify({ results: [{
    txHash: hash,
    to: '0xa513e6e4b8f2a923d98304ec87f64353c4d5c853',
    selector: data.slice(0, 10),
    success: receipt.status === 'success'
  }], error: null });
}