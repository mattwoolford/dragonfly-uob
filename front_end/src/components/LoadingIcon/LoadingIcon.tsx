import Logo from "@components/Logo/Logo.tsx";


export default function LoadingIcon(){

    return (
        <div className={"LoadingIcon"}>
            <Logo animateTimes={Infinity} />
            <p>Loading...</p>
        </div>
    )

}
