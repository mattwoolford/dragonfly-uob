import {
    Activity,
    type MouseEventHandler,
    type ReactEventHandler,
    useEffect,
    useRef,
    useState
}             from "react";
import socket from "../../socket";
import Logo   from "@assets/logo/png/DragonFly Logo_Emblem.png";


interface ImageCanvasProps {
    onPixelClick?: (x: number, y: number) => void;
    socketEvent?: string;
}

type ImageSocketPayload = {
    data: {
        image: ArrayBuffer
    }
};

export default function ImageCanvas({ socketEvent = "image-inspection" }: ImageCanvasProps) {

    const [imageSrc, setImageSrc] = useState<string | null>(null);
    const imgRef = useRef<HTMLImageElement>(null);

    const handleClick: MouseEventHandler<HTMLImageElement> = (e) => {

        if (!imgRef.current) return;

        const rect = imgRef.current.getBoundingClientRect();
        const scaleX = imgRef.current.naturalWidth / rect.width;
        const scaleY = imgRef.current.naturalHeight / rect.height;

        const u = Math.round((e.clientX - rect.left) * scaleX);
        const v = Math.round((e.clientY - rect.top) * scaleY);

        console.log("Image click", u, v);

        socket.emit("pixel-coordinates-selected", {
            data: {
                u,
                v
            }
        });

    };

    const handleError: ReactEventHandler<HTMLImageElement> = (e) => {
        e.currentTarget.setAttribute("src", Logo);
    };

    useEffect(() => {

        socket.on(socketEvent, (payload: ImageSocketPayload) => {
            const imagePayload = payload.data.image;

            const blob = new Blob([imagePayload], { type: "image/jpeg" });
            setImageSrc(URL.createObjectURL(blob));
        });

        return () => {
            socket.off(socketEvent);
        };
    }, [socketEvent]);


    return (
        <div className={"ImageCanvas"}>
            <div className={"ImageCanvas__background"}>
                <img className={"size-40"} src={Logo} alt={"DragonFly Logo"}/>
                <p>Mission not started</p>
            </div>
            <Activity mode={ imageSrc ? "visible" : "hidden"}>
                <img
                    ref={imgRef}
                    src={imageSrc ?? ""}
                    onClick={handleClick}
                    className={"ImageCanvas__image"}
                    alt={ "Air Imagery" }
                    onError={handleError}
                />
            </Activity>
        </div>
    );
}
