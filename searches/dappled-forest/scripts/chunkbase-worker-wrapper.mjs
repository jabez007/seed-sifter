import { parentPort, workerData } from 'node:worker_threads';

const listeners = [];

globalThis.addEventListener = (type, callback) => {
  if (type === 'message') listeners.push(callback);
};

globalThis.postMessage = (message) => parentPort.postMessage(message);
globalThis.start = () => {};
globalThis.self = globalThis;

parentPort.on('message', (data) => {
  for (const callback of listeners) callback({ data, origin: '*' });
});

if (!workerData?.workerPath) {
  throw new Error('workerData.workerPath is required');
}

await import(workerData.workerPath);
