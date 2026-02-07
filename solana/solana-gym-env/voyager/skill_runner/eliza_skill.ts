import { Transaction, SystemProgram, PublicKey, Keypair, NONCE_ACCOUNT_LENGTH } from '@solana/web3.js';

export async function executeSkill(blockhash: string): Promise<string> {
    const tx = new Transaction();
    const agentPubkey = new PublicKey('C7QGU41Xj2itqYZSmyHH7iXHCetXQMMhQ3NRJxvtWKUz');
    const connection = new (await import('@solana/web3.js')).Connection('http://localhost:8899');

    // Create a fresh nonce account for operations
    const nonceKp = Keypair.generate();
    const newAuthority = Keypair.generate();

    tx.add(SystemProgram.createAccount({
        fromPubkey: agentPubkey,
        newAccountPubkey: nonceKp.publicKey,
        lamports: 1447680,
        space: 80,
        programId: SystemProgram.programId,
    }));

    // Disc 6: InitializeNonceAccount (again for this nonce)
    tx.add(SystemProgram.nonceInitialize({
        noncePubkey: nonceKp.publicKey,
        authorizedPubkey: agentPubkey,
    }));

    // Disc 9: AllocateWithSeed
    const seed2 = 'alloc1';
    const allocSeedPubkey = await PublicKey.createWithSeed(agentPubkey, seed2, SystemProgram.programId);
    // First create the account with seed, then we get disc 3 + disc 9 is different
    // Actually AllocateWithSeed is disc 9 - we need a raw instruction
    tx.add({
        keys: [
            { pubkey: allocSeedPubkey, isSigner: false, isWritable: true },
            { pubkey: agentPubkey, isSigner: true, isWritable: false },
        ],
        programId: SystemProgram.programId,
        // AllocateWithSeed: disc=9, then base(32), seed_len(u64)+seed, space(u64), owner(32)
        data: (() => {
            const seedBuf = Buffer.from(seed2);
            const buf = Buffer.alloc(4 + 32 + 8 + seedBuf.length + 8 + 32);
            buf.writeUInt32LE(9, 0); // instruction index
            new PublicKey(agentPubkey.toBase58()).toBuffer().copy(buf, 4); // base
            buf.writeBigUInt64LE(BigInt(seedBuf.length), 36); // seed length
            seedBuf.copy(buf, 44); // seed
            buf.writeBigUInt64LE(BigInt(10), 44 + seedBuf.length); // space
            SystemProgram.programId.toBuffer().copy(buf, 52 + seedBuf.length); // owner
            return buf;
        })(),
    });

    // Disc 10: AssignWithSeed
    const seed3 = 'assgn1';
    const assignSeedPubkey = await PublicKey.createWithSeed(agentPubkey, seed3, SystemProgram.programId);
    tx.add({
        keys: [
            { pubkey: assignSeedPubkey, isSigner: false, isWritable: true },
            { pubkey: agentPubkey, isSigner: true, isWritable: false },
        ],
        programId: SystemProgram.programId,
        data: (() => {
            const seedBuf = Buffer.from(seed3);
            const buf = Buffer.alloc(4 + 32 + 8 + seedBuf.length + 32);
            buf.writeUInt32LE(10, 0); // instruction index
            new PublicKey(agentPubkey.toBase58()).toBuffer().copy(buf, 4); // base
            buf.writeBigUInt64LE(BigInt(seedBuf.length), 36); // seed length
            seedBuf.copy(buf, 44); // seed
            SystemProgram.programId.toBuffer().copy(buf, 44 + seedBuf.length); // owner
            return buf;
        })(),
    });

    tx.recentBlockhash = blockhash;
    tx.feePayer = agentPubkey;
    tx.partialSign(nonceKp);

    return tx.serialize({
        requireAllSignatures: false,
        verifySignatures: false,
    }).toString('base64');
}
