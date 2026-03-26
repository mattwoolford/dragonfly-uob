import { createContext } from "react";


export type MissionStatus = string;

export const DEFAULT_MISSION_STATUS = "Mission not started" satisfies MissionStatus;

const MissionStatusAPI = createContext<MissionStatus>(DEFAULT_MISSION_STATUS);

export default MissionStatusAPI;
