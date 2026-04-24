import { Injectable, OnDestroy } from '@angular/core';
import { Subject } from 'rxjs';
import { environment } from '../../environments/environment';

export interface WsEvento {
  evento: string;
  nro_radicado?: string;
  mensaje: string;
}

@Injectable({ providedIn: 'root' })
export class WebsocketService implements OnDestroy {
  private ws: WebSocket | null = null;
  private pingInterval: any = null;
  private reconectarTimeout: any = null;
  private destruido = false;

  readonly eventos$ = new Subject<WsEvento>();

  conectar(token: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this.destruido = false;
    this._abrir(token);
  }

  private _abrir(token: string): void {
    const url = `${environment.wsUrl}?token=${token}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this._iniciarPing();
    };

    this.ws.onmessage = (event) => {
      if (event.data === 'pong') return;
      try {
        const data: WsEvento = JSON.parse(event.data);
        this.eventos$.next(data);
      } catch {}
    };

    this.ws.onclose = () => {
      this._limpiarPing();
      if (!this.destruido) {
        // Reconectar tras 5 segundos
        this.reconectarTimeout = setTimeout(() => this._abrir(token), 5000);
      }
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  private _iniciarPing(): void {
    this._limpiarPing();
    // Ping cada 8 minutos para mantener el F1 activo durante la sesión
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send('ping');
      }
    }, 8 * 60 * 1000);
  }

  private _limpiarPing(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  desconectar(): void {
    this.destruido = true;
    this._limpiarPing();
    if (this.reconectarTimeout) {
      clearTimeout(this.reconectarTimeout);
      this.reconectarTimeout = null;
    }
    this.ws?.close();
    this.ws = null;
  }

  ngOnDestroy(): void {
    this.desconectar();
    this.eventos$.complete();
  }
}
