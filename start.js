/**
 * H.I.R.E. — Single-command startup
 *
 * Usage (from project root):
 *   npm start
 *
 * What it does:
 *   1. Finds the Python venv (root .venv → backend/venv → system py)
 *   2. Frees port 8000, then starts the FastAPI backend via uvicorn
 *   3. Waits until the backend is accepting connections
 *   4. Starts the Vite frontend dev server on port 5173
 *   5. Opens Microsoft Edge (Bing's browser) at http://localhost:5173
 *   6. Ctrl-C gracefully kills both processes
 */

const { spawn, exec } = require('child_process');
const net = require('net');
const path = require('path');
const fs = require('fs');

const root        = __dirname;
const backendDir  = path.join(root, 'backend');
const frontendDir = path.join(root, 'frontend');

const BACKEND_PORT       = 8000;
const FRONTEND_PORT      = 5173;
const BACKEND_TIMEOUT_MS = 30000;
const BROWSER_DELAY_MS   = 3500;

// ─── Python resolution ────────────────────────────────────────────────────────
function getPythonCommand() {
  if (process.env.PYTHON)     return process.env.PYTHON;
  if (process.env.PYTHON_EXE) return process.env.PYTHON_EXE;

  // Priority 1 — root-level .venv (where pip install was run)
  const rootVenv = process.platform === 'win32'
    ? path.join(root, '.venv', 'Scripts', 'python.exe')
    : path.join(root, '.venv', 'bin', 'python');

  if (fs.existsSync(rootVenv)) return rootVenv;

  // Priority 2 — backend-level venv
  const backendVenv = process.platform === 'win32'
    ? path.join(backendDir, 'venv', 'Scripts', 'python.exe')
    : path.join(backendDir, 'venv', 'bin', 'python');

  if (fs.existsSync(backendVenv)) return backendVenv;

  // Priority 3 — system Python
  return process.platform === 'win32' ? 'py' : 'python3';
}

// ─── Port helpers ─────────────────────────────────────────────────────────────
function isPortFree(port) {
  return new Promise(resolve => {
    const srv = net.createServer();
    srv.once('error', () => resolve(false));
    srv.once('listening', () => srv.close(() => resolve(true)));
    srv.listen(port, '127.0.0.1');
  });
}

/**
 * Kill processes on *port*, but only if they look like Python/Node.js processes
 * (uvicorn, python, node, npm).  Unrelated apps on the same port are left alone
 * and a warning is printed instead.
 */
function killPort(port) {
  return new Promise(resolve => {
    if (process.platform === 'win32') {
      exec(`netstat -ano -p tcp | findstr :${port}`, (err, out) => {
        if (err || !out) { resolve(); return; }
        const pids = [...new Set(
          out.split(/\r?\n/)
             .map(l => (l.match(/\s+(\d+)\s*$/) || [])[1])
             .filter(p => p && p !== '0')
        )];
        if (!pids.length) { resolve(); return; }

        let rem = pids.length;
        pids.forEach(pid => {
          // Check the process image name before killing.
          exec(`tasklist /FI "PID eq ${pid}" /NH /FO CSV`, (e2, info) => {
            const name = (info || '').toLowerCase();
            const isOurs = /python|uvicorn|node|npm/.test(name);
            if (isOurs) {
              exec(`taskkill /F /PID ${pid}`, () => { if (--rem === 0) resolve(); });
            } else {
              console.warn(`[startup]  ⚠ Port ${port} held by unrelated process (PID ${pid}) — skipping kill.`);
              if (--rem === 0) resolve();
            }
          });
        });
      });
    } else {
      // On Unix, check via ps before killing.
      exec(`lsof -ti tcp:${port}`, (err, out) => {
        if (err || !out) { resolve(); return; }
        const pids = out.trim().split(/\s+/).filter(Boolean);
        let rem = pids.length;
        pids.forEach(pid => {
          exec(`ps -p ${pid} -o comm=`, (e2, comm) => {
            const name = (comm || '').toLowerCase();
            const isOurs = /python|uvicorn|node|npm/.test(name);
            if (isOurs) {
              exec(`kill -9 ${pid}`, () => { if (--rem === 0) resolve(); });
            } else {
              console.warn(`[startup]  ⚠ Port ${port} held by unrelated process (PID ${pid}: ${comm.trim()}) — skipping kill.`);
              if (--rem === 0) resolve();
            }
          });
        });
      });
    }
  });
}

/**
 * Poll the /health HTTP endpoint until it returns 200 or the timeout elapses.
 * This verifies the app is actually serving requests, not just that the TCP
 * port is open (uvicorn binds the port briefly before the app is ready).
 */
function waitForHealth(port, timeoutMs = BACKEND_TIMEOUT_MS) {
  const http = require('http');
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + timeoutMs;
    const try_ = () => {
      const req = http.get(
        { host: '127.0.0.1', port, path: '/api/v1/health', timeout: 800 },
        res => {
          res.resume(); // drain
          if (res.statusCode === 200) { resolve(); }
          else { Date.now() < deadline ? setTimeout(try_, 400) : reject(new Error(`Health check failed (HTTP ${res.statusCode})`)); }
        }
      );
      req.on('error', () => {
        Date.now() < deadline ? setTimeout(try_, 400) : reject(new Error(`Timed out waiting for backend on port ${port}`));
      });
      req.on('timeout', () => { req.destroy(); });
    };
    try_();
  });
}


// ─── Open Microsoft Edge (Bing's browser) ────────────────────────────────────
function openEdge(url) {
  console.log(`\nOpening Microsoft Edge → ${url}\n`);

  if (process.platform === 'win32') {
    // Try Edge directly, fall back to the system default browser
    exec(`start "" "microsoft-edge:${url}"`, err => {
      if (err) exec(`start "" "${url}"`, () => {});
    });
  } else if (process.platform === 'darwin') {
    exec(`open -a "Microsoft Edge" "${url}" || open "${url}"`, () => {});
  } else {
    exec(`microsoft-edge "${url}" || xdg-open "${url}"`, () => {});
  }
}

// ─── Process launchers ────────────────────────────────────────────────────────
function startBackend(pythonCmd, port) {
  console.log(`[backend]  Starting FastAPI on http://127.0.0.1:${port} ...`);
  console.log(`[backend]  Python → ${pythonCmd}`);

  const proc = spawn(
    pythonCmd,
    ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(port), '--reload'],
    {
      cwd:         backendDir,
      stdio:       'inherit',
      env:         { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
      windowsHide: false,
    }
  );
  proc.on('error', err => console.error('[backend]  Failed to start:', err.message));
  return proc;
}

function startFrontend(frontendPort, backendPort) {
  console.log(`[frontend] Starting Vite on http://localhost:${frontendPort} ...`);

  const env = {
    ...process.env,
    VITE_API_TARGET: `http://127.0.0.1:${backendPort}`,
  };

  // Windows: launch via cmd.exe to avoid spawn EINVAL
  const proc = process.platform === 'win32'
    ? spawn(
        process.env.ComSpec || 'cmd.exe',
        ['/d', '/s', '/c', `npm run dev -- --port ${frontendPort} --host 0.0.0.0`],
        { cwd: frontendDir, stdio: 'inherit', env, windowsHide: false }
      )
    : spawn(
        'npm',
        ['run', 'dev', '--', '--port', String(frontendPort), '--host', '0.0.0.0'],
        { cwd: frontendDir, stdio: 'inherit', env }
      );

  proc.on('error', err => console.error('[frontend] Failed to start:', err.message));
  return proc;
}

// ─── Main ─────────────────────────────────────────────────────────────────────
async function main() {
  console.log('');
  console.log('╔══════════════════════════════════════════╗');
  console.log('║       H.I.R.E.  —  Starting up...       ║');
  console.log('╚══════════════════════════════════════════╝');
  console.log('');

  // Sanity checks
  if (!fs.existsSync(backendDir))  throw new Error(`Backend directory not found:\n  ${backendDir}`);
  if (!fs.existsSync(frontendDir)) throw new Error(`Frontend directory not found:\n  ${frontendDir}`);

  const pythonCmd = getPythonCommand();

  console.log(`Root:      ${root}`);
  console.log(`Backend:   ${backendDir}`);
  console.log(`Frontend:  ${frontendDir}`);
  console.log(`Python:    ${pythonCmd}`);
  console.log('');

  // ── Backend ──
  await killPort(BACKEND_PORT);

  const backendFree = await isPortFree(BACKEND_PORT);
  let backend = null;

  if (backendFree) {
    backend = startBackend(pythonCmd, BACKEND_PORT);

    try {
      await waitForHealth(BACKEND_PORT);
      console.log(`[backend]  ✓ Ready at http://127.0.0.1:${BACKEND_PORT}`);
    } catch (err) {
      console.error(`[backend]  ✗ ${err.message}`);
      backend?.kill();
      process.exit(1);
    }
  } else {
    console.log(`[backend]  ✓ Already running at http://127.0.0.1:${BACKEND_PORT}`);
  }

  console.log('');

  // ── Frontend ──
  const frontend = startFrontend(FRONTEND_PORT, BACKEND_PORT);

  // ── Open Edge after Vite is ready ──
  setTimeout(() => {
    console.log('');
    console.log('╔══════════════════════════════════════════╗');
    console.log(`║  Frontend → http://localhost:${FRONTEND_PORT}      ║`);
    console.log(`║  Backend  → http://127.0.0.1:${BACKEND_PORT}       ║`);
    console.log('║  Press Ctrl-C to stop both servers       ║');
    console.log('╚══════════════════════════════════════════╝');
    openEdge(`http://localhost:${FRONTEND_PORT}`);
  }, BROWSER_DELAY_MS);

  // ── Graceful shutdown ──
  let stopping = false;
  const stopAll = () => {
    if (stopping) return;
    stopping = true;
    console.log('\n\nStopping H.I.R.E...');
    backend?.kill();
    frontend?.kill();
    process.exit(0);
  };

  process.on('SIGINT',  stopAll);
  process.on('SIGTERM', stopAll);

  backend?.on('close', code => {
    if (!stopping && code !== 0 && code !== null)
      console.error(`[backend]  exited with code ${code}`);
  });
  frontend.on('close', code => {
    if (!stopping && code !== 0 && code !== null)
      console.error(`[frontend] exited with code ${code}`);
  });

  // Keep process alive
  await new Promise(() => {});
}

main().catch(err => {
  console.error('\n╔══════════════════════════════════════════╗');
  console.error('║           Startup failed                 ║');
  console.error('╚══════════════════════════════════════════╝');
  console.error(err.message || err);
  process.exit(1);
});