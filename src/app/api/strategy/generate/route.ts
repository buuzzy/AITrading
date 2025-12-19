import { NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';
import { auth } from "@/auth";
import { getUserCredits, decreaseCredits, CreditsTransType } from "@/services/credit";

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  try {
    // 1. Authenticate & Deduct Credits
    const session = await auth();
    if (!session?.user?.uuid) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const userId = session.user.uuid;
    const userCredits = await getUserCredits(userId);

    // Strict Check: Ensure user has enough credits
    if (userCredits.left_credits < 1) {
      return NextResponse.json({ 
        error: 'Insufficient credits',
        details: 'You need at least 1 credit to generate a strategy.' 
      }, { status: 402 }); // 402 Payment Required
    }

    // Deduct Credit
    try {
        await decreaseCredits({
            user_uuid: userId,
            trans_type: CreditsTransType.StrategyGenerate,
            credits: 1
        });
    } catch (e) {
        console.error('Credit deduction failed:', e);
        return NextResponse.json({ error: 'Transaction failed' }, { status: 500 });
    }

    // 2. Parse Request
    const { messages } = await request.json();

    if (!messages || !Array.isArray(messages)) {
      return NextResponse.json({ error: 'Messages array is required' }, { status: 400 });
    }

    // Environment Setup
    const pythonScript = path.join(process.cwd(), 'specs/demo/strategy_generator.py');
    const venvPython = path.join(process.cwd(), 'venv/bin/python');
    const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python3';

    // Prepare messages JSON string
    const messagesJson = JSON.stringify(messages);

    console.log(`[Strategy Chat] Starting R1 stream via STDIN...`);

    const encoder = new TextEncoder();

    const stream = new ReadableStream({
      start(controller) {
        let isClosed = false;

        const safeEnqueue = (data: Uint8Array | string) => {
          if (isClosed) return;
          try {
            controller.enqueue(data);
          } catch (e) {
            console.warn('[Strategy Stream] Enqueue failed (stream likely closed):', e);
          }
        };

        const safeClose = () => {
          if (isClosed) return;
          isClosed = true;
          try {
            controller.close();
          } catch (e) {
            console.warn('[Strategy Stream] Close failed:', e);
          }
        };

        // Remove 'messagesJson' from args, we will write it to stdin
        const child = spawn(pythonCmd, ['-u', pythonScript]);

        // --- STDIN WRITING ---
        child.stdin.write(messagesJson);
        child.stdin.end(); // Important: Close stdin so Python knows input is done
        // ---------------------

        child.stdout.on('data', (data) => {
          safeEnqueue(data);
        });

        child.stderr.on('data', (data) => {
          console.error(`[Strategy Chat] Stderr: ${data}`);
          // Optional: Forward stderr as error json if critical
        });

        child.on('close', (code) => {
          if (code !== 0) {
             // If Python exits with error, frontend will see the stream end.
             // Usually the script itself would have printed an error JSON before exiting.
             console.log(`[Strategy Chat] Exited with code ${code}`);
          }
          safeClose();
        });

        child.on('error', (err) => {
          const errorJson = JSON.stringify({ type: 'error', message: `Spawn Error: ${err.message}` }) + "\n";
          safeEnqueue(encoder.encode(errorJson));
          safeClose();
        });
      }
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'application/x-ndjson',
        'Transfer-Encoding': 'chunked',
      },
    });

  } catch (error: any) {
    console.error('[Strategy Chat] Error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}