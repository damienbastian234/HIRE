const { spawn } = require('child_process');
const net = require('net');
const path = require('path');
const fs = require('fs');
const { exec } = require('child_process');

const root = __dirname;
const backendDir = path.join(root, 'backend');
const frontendDir = path.join(root, 'frontend');
const npmCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm';

function getPythonCommand() {
  if (process.env.PYTHON) return process.env.PYTHON;
  if (process.env.PYTHON_EXE) return process.env.PYTHON_EXE;

  if (process.platform === 'win32') {
    const candidatePaths = [
      path.join(process.env.USERPROFILE || '', 'AppData', 'Local', 'Programs', 'Python', 'Python312', 'python.exe'),
      path.join(process.env.USERPROFILE || '', 'AppData', 'Local', 'Programs', 'Python', 'Python311', 'python.exe'),
      path.join(process.env.USERPROFILE || '', 'AppData', 'Local', 'Microsoft', 'WindowsApps', 'python.exe'),
    ];

    const existing = candidatePaths.find((candidate) => fs.existsSync(candidate));
    if (existing) return existing;

    return 'py';
  }

  return 'python';
}

const pythonCmd = getPythonCommand();

function isPortAvailable(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once('error', () => resolve(false));
    server.once('listening', () => {
      server.close(() => resolve(true));
    });
    server.listen(port, '127.0.0.1');
  });
}

function killProcessesOnPort(port) {
  return new Promise((resolve) => {
    if (process.platform === 'win32') {
      exec(`netstat -ano -p tcp | findstr :${port}`, (error, stdout) => {
        const pids = [...stdout.matchAll(/\s(\d+)\s*$/gm)].map((match) => match[1]);
        const uniquePids = [...new Set(pids)];
        if (!uniquePids.length) {
          resolve();
          return;
        }

        const killNext = () => {
          const pid = uniquePids.shift();
          if (!pid) {
            resolve();
            return;
          }

          exec(`taskkill /F /PID ${pid}`, () => killNext());
        };

        killNext();
      });
    } else {
      exec(`lsof -ti tcp:${port} | xargs -r kill -9`, () => resolve());
    }
  });
}

async function getAvailablePort(startPort) {
  let port = startPort;
  while (true) {
    await killProcessesOnPort(port);
    if (await isPortAvailable(port)) {
      return port;
    }
    port += 1;
  }
}

function waitForServer(port, timeoutMs = 20000) {
  return new Promise((resolve, reject) => {
    const startedAt = Date.now();

    const attempt = () => {
      const socket = net.createConnection({ host: '127.0.0.1', port });
      socket.setTimeout(500);
      socket.on('connect', () => {
        socket.end();
        resolve();
      });
      socket.on('timeout', () => {
        socket.destroy();
        if (Date.now() - startedAt > timeoutMs) {
          reject(new Error(`Timed out waiting for backend on port ${port}`));
        } else {
          setTimeout(attempt, 250);
        }
      });
      socket.on('error', () => {
        if (Date.now() - startedAt > timeoutMs) {
          reject(new Error(`Timed out waiting for backend on port ${port}`));
        } else {
          setTimeout(attempt, 250);
        }
      });
    };

    attempt();
  });
}

async function main() {
  const backendPort = 8000;
  await killProcessesOnPort(backendPort);
  const frontendPort = await getAvailablePort(5173);

  const backendAvailable = await isPortAvailable(backendPort);
  if (backendAvailable) {
    console.log(`Starting backend on http://127.0.0.1:${backendPort}...`);
  } else {
    console.log(`Backend already running on http://127.0.0.1:${backendPort}; reusing it.`);
  }

  const backendEnv = {
    ...process.env,
    VITE_API_TARGET: `http://127.0.0.1:${backendPort}`,
  };

  const backend = backendAvailable
    ? spawn(pythonCmd, ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(backendPort)], {
        cwd: backendDir,
        stdio: 'inherit',
        env: backendEnv,
      })
    : null;

  if (backend) {
    try {
      await waitForServer(backendPort);
    } catch (error) {
      console.error(error.message);
      backend.kill();
      process.exit(1);
    }
  }

  console.log(`Starting frontend on http://localhost:${frontendPort}...`);
  const frontend = spawn(npmCmd, ['run', 'dev', '--', '--host', '0.0.0.0', '--port', String(frontendPort)], {
    cwd: frontendDir,
    stdio: 'inherit',
    shell: true,
    env: {
      ...process.env,
      VITE_API_TARGET: `http://127.0.0.1:${backendPort}`,
      VITE_PORT: String(frontendPort),
    },
  });

  const openInEdge = () => {
    const url = `http://localhost:${frontendPort}`;
    const edgeCmd = process.platform === 'win32' ? 'start microsoft-edge:' + url : 'xdg-open ' + url;
    exec(edgeCmd, () => {});
  };

  frontend.on('spawn', () => {
    setTimeout(openInEdge, 2000);
  });

  const stopAll = () => {
    if (backend) backend.kill();
    frontend.kill();
    process.exit(0);
  };

  backend?.on('close', (code) => {
    if (code !== 0) {
      console.error('Backend exited with code', code);
    }
  });

  frontend.on('close', (code) => {
    if (code !== 0) {
      console.error('Frontend exited with code', code);
    }
  });

  process.on('SIGINT', stopAll);
  process.on('SIGTERM', stopAll);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
