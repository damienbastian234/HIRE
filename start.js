const { spawn, exec } = require('child_process');
const net = require('net');
const path = require('path');
const fs = require('fs');

const root = __dirname;
const backendDir = path.join(root, 'backend');
const frontendDir = path.join(root, 'frontend');

const BACKEND_PORT = 8000;
const FRONTEND_START_PORT = 5173;

function getPythonCommand() {
  if (process.env.PYTHON) return process.env.PYTHON;
  if (process.env.PYTHON_EXE) return process.env.PYTHON_EXE;

  if (process.platform === 'win32') {
    const candidatePaths = [
      path.join(
        process.env.USERPROFILE || '',
        'AppData',
        'Local',
        'Programs',
        'Python',
        'Python312',
        'python.exe'
      ),
      path.join(
        process.env.USERPROFILE || '',
        'AppData',
        'Local',
        'Programs',
        'Python',
        'Python311',
        'python.exe'
      ),
      path.join(
        process.env.USERPROFILE || '',
        'AppData',
        'Local',
        'Microsoft',
        'WindowsApps',
        'python.exe'
      ),
    ];

    const existing = candidatePaths.find((candidate) =>
      fs.existsSync(candidate)
    );

    if (existing) {
      return existing;
    }

    return 'py';
  }

  return 'python3';
}

const pythonCmd = getPythonCommand();

function isPortAvailable(port) {
  return new Promise((resolve) => {
    const server = net.createServer();

    server.once('error', () => {
      resolve(false);
    });

    server.once('listening', () => {
      server.close(() => {
        resolve(true);
      });
    });

    server.listen(port, '127.0.0.1');
  });
}

function killProcessesOnPort(port) {
  return new Promise((resolve) => {
    if (process.platform === 'win32') {
      exec(
        `netstat -ano -p tcp | findstr :${port}`,
        (error, stdout) => {
          if (error || !stdout) {
            resolve();
            return;
          }

          const pids = [];

          for (const line of stdout.split(/\r?\n/)) {
            const match = line.match(/\s+(\d+)\s*$/);

            if (match) {
              pids.push(match[1]);
            }
          }

          const uniquePids = [...new Set(pids)];

          // Do not kill PID 0
          const validPids = uniquePids.filter((pid) => pid !== '0');

          if (!validPids.length) {
            resolve();
            return;
          }

          let remaining = validPids.length;

          for (const pid of validPids) {
            exec(`taskkill /F /PID ${pid}`, () => {
              remaining--;

              if (remaining === 0) {
                resolve();
              }
            });
          }
        }
      );
    } else {
      exec(
        `lsof -ti tcp:${port} | xargs -r kill -9`,
        () => resolve()
      );
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

    port++;
  }
}

function waitForServer(port, timeoutMs = 20000) {
  return new Promise((resolve, reject) => {
    const startedAt = Date.now();

    const attempt = () => {
      const socket = net.createConnection({
        host: '127.0.0.1',
        port,
      });

      socket.setTimeout(500);

      socket.on('connect', () => {
        socket.destroy();
        resolve();
      });

      socket.on('timeout', () => {
        socket.destroy();

        if (Date.now() - startedAt > timeoutMs) {
          reject(
            new Error(
              `Timed out waiting for backend on port ${port}`
            )
          );
        } else {
          setTimeout(attempt, 250);
        }
      });

      socket.on('error', () => {
        socket.destroy();

        if (Date.now() - startedAt > timeoutMs) {
          reject(
            new Error(
              `Timed out waiting for backend on port ${port}`
            )
          );
        } else {
          setTimeout(attempt, 250);
        }
      });
    };

    attempt();
  });
}

function startBackend(port) {
  console.log(
    `Starting backend on http://127.0.0.1:${port}...`
  );

  const backendEnv = {
    ...process.env,
    VITE_API_TARGET: `http://127.0.0.1:${port}`,
  };

  const backend = spawn(
    pythonCmd,
    [
      '-m',
      'uvicorn',
      'app.main:app',
      '--host',
      '127.0.0.1',
      '--port',
      String(port),
    ],
    {
      cwd: backendDir,
      stdio: 'inherit',
      env: backendEnv,
      windowsHide: false,
    }
  );

  backend.on('error', (error) => {
    console.error('Failed to start backend:', error);
  });

  return backend;
}

function startFrontend(port, backendPort) {
  console.log(
    `Starting frontend on http://localhost:${port}...`
  );

  const frontendEnv = {
    ...process.env,
    VITE_API_TARGET: `http://127.0.0.1:${backendPort}`,
    VITE_PORT: String(port),
  };

  /*
   * IMPORTANT:
   *
   * On Windows, instead of spawning npm.cmd directly,
   * launch it through cmd.exe.
   *
   * This avoids the "spawn EINVAL" problem that can occur
   * with npm.cmd on Windows.
   */

  let frontend;

  if (process.platform === 'win32') {
    frontend = spawn(
      process.env.ComSpec || 'cmd.exe',
      [
        '/d',
        '/s',
        '/c',
        `npm run dev -- --host 0.0.0.0 --port ${port}`,
      ],
      {
        cwd: frontendDir,
        stdio: 'inherit',
        env: frontendEnv,
        windowsHide: false,
      }
    );
  } else {
    frontend = spawn(
      'npm',
      [
        'run',
        'dev',
        '--',
        '--host',
        '0.0.0.0',
        '--port',
        String(port),
      ],
      {
        cwd: frontendDir,
        stdio: 'inherit',
        env: frontendEnv,
      }
    );
  }

  frontend.on('error', (error) => {
    console.error('Failed to start frontend:', error);
  });

  return frontend;
}

function openInEdge(port) {
  const url = `http://localhost:${port}`;

  if (process.platform === 'win32') {
    exec(`start "" microsoft-edge:"${url}"`, () => {});
  } else if (process.platform === 'darwin') {
    exec(`open "${url}"`, () => {});
  } else {
    exec(`xdg-open "${url}"`, () => {});
  }
}

async function main() {
  console.log('');
  console.log('========================================');
  console.log('        H.I.R.E Application Startup');
  console.log('========================================');
  console.log('');

  // Validate required directories first.
  if (!fs.existsSync(backendDir)) {
    throw new Error(
      `Backend directory not found:\n${backendDir}`
    );
  }

  if (!fs.existsSync(frontendDir)) {
    throw new Error(
      `Frontend directory not found:\n${frontendDir}`
    );
  }

  console.log(`Root:     ${root}`);
  console.log(`Backend:  ${backendDir}`);
  console.log(`Frontend: ${frontendDir}`);
  console.log('');

  // Clean backend port.
  await killProcessesOnPort(BACKEND_PORT);

  // Find a free frontend port.
  const frontendPort = await getAvailablePort(
    FRONTEND_START_PORT
  );

  /*
   * Start backend.
   */
  const backendAvailable = await isPortAvailable(
    BACKEND_PORT
  );

  let backend = null;

  if (backendAvailable) {
    backend = startBackend(BACKEND_PORT);

    try {
      await waitForServer(BACKEND_PORT);

      console.log(
        `Backend ready at http://127.0.0.1:${BACKEND_PORT}`
      );
    } catch (error) {
      console.error(
        'Backend failed to start:',
        error.message
      );

      if (backend) {
        backend.kill();
      }

      process.exit(1);
    }
  } else {
    console.log(
      `Backend already running on http://127.0.0.1:${BACKEND_PORT}`
    );
  }

  /*
   * Start frontend.
   */
  const frontend = startFrontend(
    frontendPort,
    BACKEND_PORT
  );

  /*
   * Give Vite a moment to start, then open Edge.
   */
  setTimeout(() => {
    console.log('');
    console.log(
      `Frontend should be available at http://localhost:${frontendPort}`
    );
    console.log('');

    openInEdge(frontendPort);
  }, 3000);

  /*
   * Shutdown everything when CTRL+C is pressed.
   */
  const stopAll = async () => {
    console.log('');
    console.log('Stopping H.I.R.E...');

    if (backend) {
      backend.kill();
    }

    if (frontend) {
      frontend.kill();
    }

    process.exit(0);
  };

  process.on('SIGINT', stopAll);
  process.on('SIGTERM', stopAll);

  backend?.on('close', (code) => {
    if (code !== 0 && code !== null) {
      console.error(
        `Backend exited with code ${code}`
      );
    }
  });

  frontend.on('close', (code) => {
    if (code !== 0 && code !== null) {
      console.error(
        `Frontend exited with code ${code}`
      );
    }
  });

  /*
   * Keep this Node process alive.
   */
  await new Promise(() => {});
}

main().catch((error) => {
  console.error('');
  console.error('========================================');
  console.error('Startup failed');
  console.error('========================================');
  console.error('');
  console.error(error);
  console.error('');

  process.exit(1);
});