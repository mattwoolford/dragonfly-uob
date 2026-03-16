import type {Socket} from "socket.io-client";
import {use} from "react";
import WebSocketAPIContext from "@utils/contexts/WebSocketsAPIContext.ts";

export default  function useSocket(): Socket {
    const socket = use(WebSocketAPIContext);
    if (!socket) {
        throw new Error("useSocket must be used within a SocketProvider");
    }
    return socket;
}
