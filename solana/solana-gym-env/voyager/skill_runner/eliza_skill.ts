import { Transaction, SystemProgram, PublicKey, Keypair } from '@solana/web3.js';
import {
    TOKEN_PROGRAM_ID, MINT_SIZE, getMinimumBalanceForRentExemptMint,
    createInitializeMint2Instruction, createInitializeAccountInstruction,
    createMintToInstruction, createTransferInstruction, createApproveInstruction,
    createRevokeInstruction, createBurnInstruction, createCloseAccountInstruction,
    createSetAuthorityInstruction, AuthorityType, createTransferCheckedInstruction,
    createApproveCheckedInstruction, createMintToCheckedInstruction,
    createBurnCheckedInstruction, createSyncNativeInstruction,
    createInitializeAccount2Instruction, createInitializeAccount3Instruction,
    ASSOCIATED_TOKEN_PROGRAM_ID, getAssociatedTokenAddressSync,
    createAssociatedTokenAccountInstruction,
} from '@solana/spl-token';

export async function executeSkill(blockhash: string): Promise<string> {
    const tx = new Transaction();
    const agentPubkey = new PublicKey('C7QGU41Xj2itqYZSmyHH7iXHCetXQMMhQ3NRJxvtWKUz');
    const connection = new (await import('@solana/web3.js')).Connection('http://localhost:8899');

    // Create mint keypair
    const mintKp = Keypair.generate();
    const mintRent = await getMinimumBalanceForRentExemptMint(connection);

    // Create mint account
    tx.add(SystemProgram.createAccount({
        fromPubkey: agentPubkey,
        newAccountPubkey: mintKp.publicKey,
        lamports: mintRent,
        space: MINT_SIZE,
        programId: TOKEN_PROGRAM_ID,
    }));

    // Disc 20: InitializeMint2 (no rent sysvar needed)
    tx.add(createInitializeMint2Instruction(
        mintKp.publicKey, 9, agentPubkey, agentPubkey, TOKEN_PROGRAM_ID
    ));

    // Create two token accounts for the mint
    const tokenAcct1 = Keypair.generate();
    const tokenAcct2 = Keypair.generate();
    const acctRent = await connection.getMinimumBalanceForRentExemption(165);

    // Token account 1
    tx.add(SystemProgram.createAccount({
        fromPubkey: agentPubkey,
        newAccountPubkey: tokenAcct1.publicKey,
        lamports: acctRent,
        space: 165,
        programId: TOKEN_PROGRAM_ID,
    }));

    // Disc 18: InitializeAccount3
    tx.add(createInitializeAccount3Instruction(
        tokenAcct1.publicKey, mintKp.publicKey, agentPubkey, TOKEN_PROGRAM_ID
    ));

    // Token account 2
    tx.add(SystemProgram.createAccount({
        fromPubkey: agentPubkey,
        newAccountPubkey: tokenAcct2.publicKey,
        lamports: acctRent,
        space: 165,
        programId: TOKEN_PROGRAM_ID,
    }));

    // Disc 1: InitializeAccount (original version)
    tx.add(createInitializeAccountInstruction(
        tokenAcct2.publicKey, mintKp.publicKey, agentPubkey, TOKEN_PROGRAM_ID
    ));

    // Disc 7: MintTo (mint 1000 tokens to account 1)
    tx.add(createMintToInstruction(
        mintKp.publicKey, tokenAcct1.publicKey, agentPubkey, 1000_000_000_000n,
        [], TOKEN_PROGRAM_ID
    ));

    // Disc 3: Transfer (transfer some tokens from acct1 to acct2)
    tx.add(createTransferInstruction(
        tokenAcct1.publicKey, tokenAcct2.publicKey, agentPubkey, 100_000_000_000n,
        [], TOKEN_PROGRAM_ID
    ));

    // Disc 4: Approve (approve delegate on acct1)
    tx.add(createApproveInstruction(
        tokenAcct1.publicKey, tokenAcct2.publicKey, agentPubkey, 50_000_000_000n,
        [], TOKEN_PROGRAM_ID
    ));

    // Disc 5: Revoke
    tx.add(createRevokeInstruction(
        tokenAcct1.publicKey, agentPubkey, [], TOKEN_PROGRAM_ID
    ));

    // Disc 12: TransferChecked
    tx.add(createTransferCheckedInstruction(
        tokenAcct1.publicKey, mintKp.publicKey, tokenAcct2.publicKey, agentPubkey,
        50_000_000_000n, 9, [], TOKEN_PROGRAM_ID
    ));

    // Disc 8: Burn
    tx.add(createBurnInstruction(
        tokenAcct2.publicKey, mintKp.publicKey, agentPubkey, 10_000_000_000n,
        [], TOKEN_PROGRAM_ID
    ));

    tx.recentBlockhash = blockhash;
    tx.feePayer = agentPubkey;
    tx.partialSign(mintKp, tokenAcct1, tokenAcct2);

    return tx.serialize({
        requireAllSignatures: false,
        verifySignatures: false,
    }).toString('base64');
}
