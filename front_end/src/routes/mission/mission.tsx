import './mission.css';
import KeyboardEffect              from "@utils/components/KeyboardEffect/KeyboardEffect.tsx";
import LoadingIcon                 from "@components/LoadingIcon/LoadingIcon.tsx";
import ContentContainer            from "@components/ContentContainer/ContentContainer.tsx";
import {
    LayoutGroup,
    motion
}                                  from "motion/react";
import Console                     from "@components/Console/Console.tsx";
import Map                         from "@components/Map/Map.client.tsx";
import InteractionCanvas           from "@components/InteractionCanvas/InteractionCanvas.client.tsx";
import {
    startTransition,
    useCallback,
    useLayoutEffect,
    useOptimistic,
    useState
}                                  from "react";
import clsx                        from "clsx";
import Button                      from "@components/Button/Button.tsx";
import socket, { DEFAULT_TIMEOUT } from "@socket";
import type { MissionStatus }      from "@utils/contexts/MissionStatusAPI.ts";


// eslint-disable-next-line react-refresh/only-export-components
export async function clientLoader() {
  const INTRO_TIME = 10000;
  await Promise.all([
                      new Promise(resolve => setTimeout(resolve, INTRO_TIME)),
                    ]);
  return null;
}


clientLoader.hydrate = true;


export function HydrateFallback() {
  return <LoadingIcon />
}


export default function Mission() {

    const DEFAULT_LOCATION_PIN = [51.423967391658536, -2.67169820644399] satisfies [number, number];

    // States
    // Whether to maximise the interaction window for user focus and input
    const [maximiseInteraction, setMaximiseInteraction] = useState<boolean>(false);
    // Whether a mission is in progress
    const [missionIsInProgress, setMissionIsInProgress] = useState<boolean>(false);
    const [optimisticMissionIsInProgress, setOptimisticMissionIsInProgress] = useOptimistic<boolean>(missionIsInProgress);

    // Callbacks
    const isMissionStatusIdle = (missionStatus: MissionStatus) => {
        return (
                    [
                        "Mission not started",
                        "Mission complete",
                        "Mission failed"
                    ] satisfies MissionStatus[] as MissionStatus[]
                ).includes(missionStatus)
    };

    const handleStartMission = () => {
        startTransition(async () => {

            setOptimisticMissionIsInProgress(true);

            await socket.timeout(DEFAULT_TIMEOUT).emitWithAck("start-mission");

            socket.timeout(DEFAULT_TIMEOUT).emit('get-mission-status', (err, payload) => {
                if (err) {
                    console.warn("Could not fetch mission status: Request timed out", err);
                    return;
                }
                startTransition(() => {
                    setMissionIsInProgress(
                        !isMissionStatusIdle(payload.data.missionStatus)
                    );
                });
            })
        })
    };

    const handleInteraction = useCallback(() => {
        setMaximiseInteraction(true);
    }, []);

    const handleEndInteraction = useCallback(async () => {
        await new Promise<void>(resolve => setTimeout(() => {
            setMaximiseInteraction(false);
            resolve();
        }, 500));
    }, []);

    const imageContainerCx = clsx(
        !maximiseInteraction && "pointer-events-none",
        maximiseInteraction && "pointer-events-auto"
    );

    // Effects
    // Listen for mission status change
    useLayoutEffect(() => {

        socket.on('mission-status-change', (payload) => {
            setMissionIsInProgress(!isMissionStatusIdle(payload.data.missionStatus));
        });

        return () => {
            socket.off('mission-status-change');
        }

    }, []);

    return (
        <>
            <section className={"px-4"}>
                <p className={"font-bold text-2xl"}><KeyboardEffect showEndCursor={false}>DragonFly Mission Control</KeyboardEffect></p>
            </section>
            <motion.section className={"flex flex-row justify-between items-center gap-4 px-4 my-2 py-2 w-full min-h-100"}>
                <LayoutGroup>
                    <ContentContainer>
                        <Map pin={ DEFAULT_LOCATION_PIN } />
                    </ContentContainer>
                    <ContentContainer className={imageContainerCx} maximise={maximiseInteraction}>
                        <InteractionCanvas onImageLoad={handleInteraction}
                                           onInteractionRequest={handleInteraction}
                                           onPixelSelection={handleEndInteraction}
                                           onInteractionSelection={handleEndInteraction}
                                           onCancel={handleEndInteraction} />
                    </ContentContainer>
                </LayoutGroup>
            </motion.section>
            <motion.section className={"flex flex-col justify-start items-center gap-4"}>
                <Button theme={ "var(--color-active)" }
                        disabled={optimisticMissionIsInProgress}
                        onClick={handleStartMission}
                >{ optimisticMissionIsInProgress ? "Mission Started" : "Start Mission" }</Button>
                <Console />
            </motion.section>
        </>
    )
}
