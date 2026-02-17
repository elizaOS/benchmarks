import { startApiServer } from "../../../src/api/server";
import http from "node:http";
import process from "node:process";

export class BenchmarkRunner {
    private server: { port: number; close: () => Promise<void> } | null = null;
    public port: number = 0;

    async startServer(port: number = 0, runtime?: any) {
        // We start with no runtime to measure pure server overhead, 
        // or we can pass a runtime if we want to measure plugin loading.
        // For now we use the default behavior (no runtime) for baseline,
        // but scenarios might need to mock runtime or use a real one.
        // startApiServer internal logic handles config loading.
        this.server = await startApiServer({ port, runtime });
        this.port = this.server.port;
        console.log(`[BenchmarkRunner] Server started on port ${this.port}`);
    }

    async stopServer() {
        if (this.server) {
            await this.server.close();
            this.server = null;
            console.log("[BenchmarkRunner] Server stopped");
        }
    }

    async measure(name: string, fn: () => Promise<void>): Promise<number> {
        console.log(`[BenchmarkRunner] Starting measurement: ${name}`);
        const start = performance.now();
        try {
            await fn();
        } catch (err) {
            console.error(`[BenchmarkRunner] Measurement ${name} failed:`, err);
            throw err;
        }
        const end = performance.now();
        const duration = end - start;
        console.log(`[BenchmarkRunner] Measurement ${name}: ${duration.toFixed(2)}ms`);
        return duration;
    }

    async http(
        method: string,
        path: string,
        body?: Record<string, unknown>
    ): Promise<{ status: number; data: any; duration: number }> {
        if (!this.port) throw new Error("Server not started");

        return new Promise((resolve, reject) => {
            const start = performance.now();
            const b = body ? JSON.stringify(body) : undefined;
            const req = http.request(
                {
                    hostname: "127.0.0.1",
                    port: this.port,
                    path,
                    method,
                    headers: {
                        "Content-Type": "application/json",
                        ...(b ? { "Content-Length": Buffer.byteLength(b) } : {}),
                    },
                },
                (res) => {
                    const ch: Buffer[] = [];
                    res.on("data", (c) => ch.push(c));
                    res.on("end", () => {
                        const end = performance.now();
                        const raw = Buffer.concat(ch).toString("utf-8");
                        let data: any = {};
                        try {
                            data = JSON.parse(raw);
                        } catch {
                            data = { _raw: raw };
                        }
                        resolve({ status: res.statusCode ?? 0, data, duration: end - start });
                    });
                }
            );
            req.on("error", reject);
            if (b) req.write(b);
            req.end();
        });
    }

    async waitForReady(timeout = 30000): Promise<number> {
        const start = performance.now();
        while (performance.now() - start < timeout) {
            try {
                const { status } = await this.http("GET", "/api/status"); // Assuming /api/status exists or /api/health
                // /api/status endpoint exists in server.ts? e2e tests use /api/plugins.
                return status;
            } catch {
                await new Promise((r) => setTimeout(r, 100));
            }
        }
        throw new Error("Timeout waiting for server ready");
    }
}
