import { createContext } from "react";


export type MissionStatus = "Mission started" | "Mission not started" | "Arming aircraft" | "Taking off" | "Preparing search" | "Searching for the target" | "Delivering care kit to the target" | "Waiting for image assessment" | "Waiting for user interaction" | "Mission complete" | "Landing" | "Mission failed";

export const DEFAULT_MISSION_STATUS = "Mission not started" satisfies MissionStatus;

const MissionStatusAPI = createContext<MissionStatus>(DEFAULT_MISSION_STATUS);

export default MissionStatusAPI;
