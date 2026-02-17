import { startApiServer } from "../../../src/api/server";

async function main() {
    console.log("Starting benchmark runner...");
    try {
        // Start with no runtime (like lifecycle tests)
        const server = await startApiServer({ port: 0 });
        console.log(`Server started on port ${server.port}`);
        await server.close();
        console.log("Server closed");
    } catch (error) {
        console.error("Failed to start server:", error);
        process.exit(1);
    }
}

main();
