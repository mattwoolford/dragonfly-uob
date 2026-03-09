import Logo           from "@components/Logo/Logo.tsx";
import {
    Activity,
    useLayoutEffect,
    useState
}                     from "react";
import KeyboardEffect from "@utils/components/KeyboardEffect/KeyboardEffect.tsx";


interface LoadingIconProps {
    prompt?: string;
}


export default function LoadingIcon({prompt = "Loading..."}: LoadingIconProps){


    const [isMounted, setIsMounted] = useState(false);


    useLayoutEffect(() => {

        function handleLoadEffect() {
            setIsMounted(true);
        }

        handleLoadEffect();

    }, []);


    return (
        <div className={"LoadingIcon"}>
            <Logo animateTimes={Infinity} />
            <Activity mode={isMounted ? "visible" : "hidden"}>
                <p><KeyboardEffect>{prompt}</KeyboardEffect></p>
            </Activity>
        </div>
    )

}
