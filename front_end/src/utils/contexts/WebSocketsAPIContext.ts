import {createContext} from "react";
import type {Socket} from "socket.io-client";

const WebSocketAPIContext = createContext<Socket | null>(null);

export default WebSocketAPIContext;
