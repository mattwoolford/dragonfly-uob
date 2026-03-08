import Logo           from "@components/Logo/Logo.tsx";
import KeyboardEffect from "@utils/components/KeyboardEffect/KeyboardEffect.client.tsx";


export default function LoadingIcon(){

    return (
        <div className={"LoadingIcon"}>
            <Logo animateTimes={Infinity} />
            <p><KeyboardEffect>Loading...</KeyboardEffect></p>
        </div>
    )

}
