import { io } from "socket.io-client";


const socket = io(import.meta.env.VITE_SOCKET_URL, { autoConnect: true });

export const DEFAULT_TIMEOUT = 5000 as const;

export default socket;
