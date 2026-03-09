import './mission.css';
import LoadingIcon from "@components/LoadingIcon/LoadingIcon.tsx";


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
      <p>Loaded</p>
    </>
  )
}
