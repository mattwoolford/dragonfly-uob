import Logo from "@components/Logo/Logo.tsx";


export default function Header() {

    return (
        <header className={"Header"}>
            <span className={"Header__left"}>
                <Logo className={"size-15"} />
            </span>
            <span className={"Header__center"} />
            <span className={"Header__right"} />
        </header>
    )

}
