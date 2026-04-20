import { CommandHandler } from '../types/modules'
import { CommandSystemEvent, CommandSystemLog, isCommand, Response } from '../types/commands'

export default class WorkerProcessingEngine  {
  sessionId: String
  locale: String
  worker: Worker
  commandHandler: CommandHandler

  resolveInitialized!: () => void
  resolveContinue!: () => void

  constructor (sessionId: string, locale: string, worker: Worker, commandHandler: CommandHandler) {
    this.sessionId = sessionId
    this.locale = locale
    this.commandHandler = commandHandler
    this.worker = worker
    this.worker.onerror = console.log
    this.worker.onmessage = (event) => {
      console.log(
        '[WorkerProcessingEngine] Received event from worker: ',
        event.data.eventType
      )
      this.handleEvent(event)
    }
  }

  sendSystemEvent (name: string): void {
    const command: CommandSystemEvent = { __type__: 'CommandSystemEvent', name }
    this.commandHandler.onCommand(command).then(
      () => {},
      () => {}
    )
  }

  handleEvent (event: any): void {
    const { eventType } = event.data
    console.log('[ReactEngine] received eventType: ', eventType)
    switch (eventType) {
      case 'initialiseDone':
        console.log('[ReactEngine] received: initialiseDone')
        this.resolveInitialized()
        break

      case 'runCycleDone':
        console.log('[ReactEngine] received: event', event.data.scriptEvent)
        this.handleRunCycle(event.data.scriptEvent)
        break

      case 'error':
        console.error(
          '[ReactEngine] worker error:',
          event.data.error,
          event.data.stack
        )
        this.handleWorkerError(event.data.error, event.data.stack)
        break

      case 'workerLog':
        this.forwardWorkerLog(event.data.level, event.data.message)
        break

      default:
        console.log(
          '[ReactEngine] received unsupported flow event: ',
          eventType
        )
    }
  }

  handleWorkerError (error: string, stack: string): void {
    const message = `[Worker] Error in runCycle: ${error}${stack ? `\n${stack}` : ''}`
    this.forwardWorkerLog('error', message)
  }

  forwardWorkerLog (level: string, message: string): void {
    const command: CommandSystemLog = {
      __type__: 'CommandSystemLog',
      level,
      message,
      json_string: JSON.stringify({ level, message })
    }
    this.commandHandler.onCommand(command).then(
      () => {},
      () => {}
    )
  }

  start (): void {
    console.log('[WorkerProcessingEngine] started')
    const waitForInitialization: Promise<void> = this.waitForInitialization()

    waitForInitialization.then(
      () => {
        this.sendSystemEvent('initialized')
        this.firstRunCycle()
      },
      () => {}
    )
  }

  async waitForInitialization (): Promise<void> {
    return await new Promise<void>((resolve) => {
      this.resolveInitialized = resolve
      console.debug('[WorkerProcessingEngine] waiting for initialisation')
      this.worker.postMessage({ eventType: 'initialise' })
    })
  }

  firstRunCycle (): void {
    this.worker.postMessage({
      eventType: 'firstRunCycle',
      data: {
        sessionId: this.sessionId,
        locale: this.locale
      }
    })
  }

  nextRunCycle (response: Response): void {
    console.log('[WorkerProcessingEngine] nextRunCycle');
    this.worker.postMessage({ eventType: 'nextRunCycle', response })
  }

  terminate (): void {
    this.worker.terminate()
  }

  handleRunCycle (command: any): void {
    if (isCommand(command)) {
      this.commandHandler.onCommand(command).then(
        (response) => this.nextRunCycle(response),
        () => {}
      )
    }
  }
}
