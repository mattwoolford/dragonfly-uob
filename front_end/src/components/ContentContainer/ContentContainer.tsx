import { motion }                 from "motion/react";
import type { PropsWithChildren } from "react";


export default function ContentContainer({ children }: PropsWithChildren) {

    return (
        <motion.article className={"ContentContainer"} layout>
            {children}
        </motion.article>
    )

}
