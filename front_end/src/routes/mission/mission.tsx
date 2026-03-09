import './mission.css';
import KeyboardEffect from "@utils/components/KeyboardEffect/KeyboardEffect.tsx";
import LoadingIcon    from "@components/LoadingIcon/LoadingIcon.tsx";


export async function clientLoader() {
  // TODO: Do setup here
  await Promise.all([
                      new Promise(resolve => setTimeout(resolve, 10000))
                    ]);
  return null;
}


clientLoader.hydrate = true;


export function HydrateFallback() {
  return <LoadingIcon />
}


export default function Mission() {

  return (
    <>
      <section className={"px-4"}>
        <p className={"font-bold text-2xl"}><KeyboardEffect showEndCursor={false}>DragonFly Mission Control</KeyboardEffect></p>
      </section>
    </>
  )
}
