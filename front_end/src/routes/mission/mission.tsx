import './mission.css';
import KeyboardEffect    from "@utils/components/KeyboardEffect/KeyboardEffect.tsx";
import LoadingIcon       from "@components/LoadingIcon/LoadingIcon.tsx";
import ContentContainer  from "@components/ContentContainer/ContentContainer.tsx";
import {
    LayoutGroup,
    motion
}                        from "motion/react";
import Console           from "@components/Console/Console.tsx";
import Map               from "@components/Map/Map.client.tsx";
import InteractionCanvas from "@components/InteractionCanvas/InteractionCanvas.client.tsx";
import {
    useCallback,
    useState
}                        from "react";
import clsx              from "clsx";


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

    const [maximiseInteraction, setMaximiseInteraction] = useState<boolean>(false);

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
                    <Console />
                </LayoutGroup>
            </motion.section>
        </>
    )
}
