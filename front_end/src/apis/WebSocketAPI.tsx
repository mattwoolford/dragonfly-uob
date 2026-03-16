import WebSocketAPIContext from "@utils/contexts/WebSocketsAPIContext";
import {type PropsWithChildren, useEffect, useRef, useState} from "react";
import {io, type Socket} from "socket.io-client";

export default function WebSocketAPI({ children }: PropsWithChildren) {

    const [connectedSocket, setConnectedSocket] = useState<Socket | null>(null);
    const socketRef = useRef<Socket | null>(null);

    useEffect(() => {

        let socket = socketRef.current;

        if(!socket) {
            socket = io(import.meta.env.VITE_SOCKET_URL, { autoConnect: true });
            if(socket){
                console.log("Socket connected successfully", socket);
            }
            socketRef.current = socket;
        }

        if(!connectedSocket){
            setConnectedSocket(socket);
        }

        return () => {
            socket.disconnect();
        };

    }, [connectedSocket]);

    return (
        <WebSocketAPIContext.Provider value={connectedSocket}>
            {children}
        </WebSocketAPIContext.Provider>
    );
}
