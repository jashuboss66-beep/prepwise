import { spawn } from 'node:child_process'
import net from 'node:net'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const backendDir = path.resolve(frontendDir, '..', 'backend')
const python = process.env.PYTHON || (process.platform === 'win32' ? 'py' : 'python3')
let backendProcess = null
let webProcess = null
let stopping = false

function canBind(port) {
  return new Promise(resolve => {
    const probe = net.createServer()
    probe.once('error', () => resolve(false))
    probe.listen(port, '127.0.0.1', () => probe.close(() => resolve(true)))
  })
}

async function findBackendPort() {
  for (let port = 5000; port < 5100; port += 1) {
    if (await canBind(port)) return port
  }
  throw new Error('No free local API port was found between 5000 and 5099. Close an older Prepwise window and try again.')
}

function waitForBackend(port) {
  return new Promise((resolve, reject) => {
    let output = ''
    const timeout = setTimeout(() => reject(new Error('Flask did not report ready within 30 seconds. Check the backend output above.')), 30000)
    const onOutput = chunk => {
      const text = chunk.toString()
      process.stdout.write(text)
      output = (output + text).slice(-4000)
      if (new RegExp(`Running on http://(127\\.0\\.0\\.1|0\\.0\\.0\\.0):${port}`).test(output)) {
        clearTimeout(timeout)
        resolve()
      }
    }
    backendProcess.stdout.on('data', onOutput)
    backendProcess.stderr.on('data', onOutput)
    backendProcess.once('error', error => {
      clearTimeout(timeout)
      reject(new Error(`Could not start Flask with "${python}": ${error.message}`))
    })
    backendProcess.once('exit', code => {
      clearTimeout(timeout)
      reject(new Error(`Flask stopped during startup with exit code ${code ?? 'unknown'}. Install backend/requirements.txt and check the backend output above.`))
    })
  })
}

function stopChildren() {
  stopping = true
  if (webProcess && webProcess.exitCode === null) webProcess.kill()
  if (backendProcess && backendProcess.exitCode === null) backendProcess.kill()
}

process.on('SIGINT', stopChildren)
process.on('SIGTERM', stopChildren)

try {
  const backendPort = await findBackendPort()
  console.log(`Starting a fresh Flask API at http://127.0.0.1:${backendPort}...`)
  backendProcess = spawn(python, ['-u', 'run.py'], {
    cwd: backendDir,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env, PORT: String(backendPort), PYTHONUNBUFFERED: '1' },
  })
  await waitForBackend(backendPort)

  console.log('Starting Vite...')
  const viteEntry = path.join(frontendDir, 'node_modules', 'vite', 'bin', 'vite.js')
  webProcess = spawn(process.execPath, [viteEntry, '--host', '0.0.0.0'], {
    cwd: frontendDir,
    stdio: 'inherit',
    env: { ...process.env, VITE_API_PROXY_TARGET: `http://127.0.0.1:${backendPort}` },
  })
  webProcess.on('error', error => {
    console.error(`Could not start Vite: ${error.message}`)
    stopChildren()
    process.exitCode = 1
  })
  webProcess.on('exit', code => {
    if (!stopping) {
      stopChildren()
      process.exitCode = code ?? 1
    }
  })
  backendProcess.on('exit', code => {
    if (!stopping) {
      console.error(`Flask stopped with exit code ${code ?? 'unknown'}.`)
      stopChildren()
      process.exitCode = code ?? 1
    }
  })
} catch (error) {
  console.error(error.message)
  stopChildren()
  process.exitCode = 1
}
