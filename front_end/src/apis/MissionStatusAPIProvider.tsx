import {
    type PropsWithChildren,
    useEffect,
    useState
}                                  from "react";
import MissionStatusAPI, {
    DEFAULT_MISSION_STATUS,
    type MissionStatus
}                                  from "@utils/contexts/MissionStatusAPI.ts";
import socket, { DEFAULT_TIMEOUT } from "@socket";


export default function MissionStatusAPIProvider({ children }: PropsWithChildren) {

    const [status, setStatus] = useState<MissionStatus>(DEFAULT_MISSION_STATUS);

    useEffect(() => {

        socket.timeout(DEFAULT_TIMEOUT).emit('get-mission-status', (err: Error, payload: {
            data: {
                missionStatus: MissionStatus
            }
        }) => {
            if (err) {
                console.warn("Could not fetch the mission status: Request timed out", err);
            }
            else {
                setStatus(payload.data.missionStatus);
            }
        });

        socket.on("mission-status-change", (payload: {
            data: {
                missionStatus: MissionStatus
            }
        }) => {
            setStatus(payload['data']['missionStatus']);
        });

        return () => {
            socket.off("mission-status-change");
        }

    }, [setStatus]);

    return (
        <MissionStatusAPI value={status}>
            {children}
        </MissionStatusAPI>
    )

}
