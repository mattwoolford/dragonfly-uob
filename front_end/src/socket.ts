import {
    io,
    Socket
}                             from "socket.io-client";
import type { MissionStatus } from "@utils/contexts/MissionStatusAPI.ts";


export interface PixelSelectionPayload {
    data: {
        u: number | null;
        v: number | null
    }
}

export interface ImagePayload {
    data: {
        image: ArrayBuffer
    }
}

export type InteractionOption = {
    id: string;
    prompt: string;
    yields: unknown;
}

export type Interaction = {
    prompt?: string,
    options: InteractionOption[]
};

export interface InteractionPayload {
    data: Interaction;
}

export interface MissionStatusPayload {
    data: {
        missionStatus: MissionStatus
    }
}

export interface ServerToClientEvents {
    "image-inspection": (payload: ImagePayload) => void;
    "interaction": (payload: InteractionPayload, ack: (response: InteractionOption["id"]) => void) => void;
    "mission-status-change": (payload: MissionStatusPayload) => void;
}

export interface ClientToServerEvents {
    "get-assessment-image": (cb: (payload: ImagePayload) => void) => void;
    "get-mission-status": (cb: (payload: MissionStatusPayload) => void) => void;
    "image-inspection-pixel-coordinates-selected": (payload: PixelSelectionPayload) => void;
    "start-mission": () => void;
}


const socket: Socket<ServerToClientEvents, ClientToServerEvents> = io(import.meta.env.VITE_SOCKET_URL, { autoConnect: true });

export const DEFAULT_TIMEOUT = 5000 as const;

export default socket;
