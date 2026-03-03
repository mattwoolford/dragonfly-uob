import { type PropsWithChildren } from "react";
import Header                     from "@components/Header/Header.tsx";


export default function Page({
    children
                             }: PropsWithChildren) {

    return (
        <>
            <Header />
            <main className={"Page"}>
                {children}
            </main>
        </>
    )

}
