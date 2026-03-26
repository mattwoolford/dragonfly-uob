import {
    type MouseEventHandler,
    use,
    useCallback,
    useEffect,
    useRef,
    useState
}                                               from "react";
import {
    AnimatePresence,
    motion
}                                               from "motion/react";
import socket, { DEFAULT_TIMEOUT }              from "../../socket";
import Logo                                     from "@assets/logo/png/DragonFly Logo_Emblem.png";
import Button                                   from "@components/Button/Button.tsx";
import KeyboardEffect                           from "@utils/components/KeyboardEffect/KeyboardEffect.tsx";
import MissionStatusAPI, { type MissionStatus } from "@utils/contexts/MissionStatusAPI.ts";


interface ImageCanvasProps {
    onCancel?: () => void;
    onImageLoad?: () => void;
    onPixelClick?: (u: number, v: number) => void;
    onPixelSelection?: (u: number, v: number) => void;
    socketEvent?: string;
}

type ImageSocketPayload = {
    data: {
        image: ArrayBuffer
    }
};

type ImageDimensions = {
    height: number,
    width: number
};

type ImagePixelSelection = {
    u: number,
    v: number
};

export default function ImageCanvas({ socketEvent = "image-inspection", onCancel, onImageLoad, onPixelClick, onPixelSelection }: ImageCanvasProps) {

    // State
    // Pixel coordinates that have been selected by the user
    const [selectedPixels, setSelectedPixels] = useState<ImagePixelSelection | null>(null);
    // Pixel coordinates that have been selected by the user, used independently for marking the location
    const [selectedMarker, setSelectedMarker] = useState<ImagePixelSelection | null>(null);
    // Whether a submission of selected pixels has been made, or the operation has been cancelled
    const [submitted, setSubmitted] = useState<boolean>(false);
    // The source image data / URI
    const [imageSrc, setImageSrc] = useState<string | null>(null);
    // The dimensions of the image
    const [imageDimensions, setImageDimensions] = useState<ImageDimensions | null>(null);


    // Context
    const missionStatus = use(MissionStatusAPI);
    const STATIC_MISSION_STATUSES: MissionStatus[] = ["Mission not started", "Target found", "Mission complete"];
    const shouldBlinkMissionStatus = !!missionStatus && !STATIC_MISSION_STATUSES.includes(missionStatus);


    // Refs
    // The canvas being drawn to display the image and marker
    const canvasRef = useRef<HTMLCanvasElement>(null);
    // The image being loaded and respectively drawn onto the canvas
    const imageRef = useRef<HTMLImageElement | null>(null);


    // Callbacks
    // Handle user clicking the canvas to select pixels
    const handlePixelSelection: MouseEventHandler<HTMLCanvasElement> = (e) => {

        if (!canvasRef.current || !imageDimensions) return;

        const rect = canvasRef.current.getBoundingClientRect();
        const scaleX = imageDimensions.width / rect.width;
        const scaleY = imageDimensions.height / rect.height;

        const u = Math.round((e.clientX - rect.left) * scaleX);
        const v = Math.round((e.clientY - rect.top) * scaleY);

        onPixelClick?.(u, v);
        setSelectedPixels({u, v});
        setSelectedMarker({u, v});

    };

    // Handle user cancelling the pixel selection operation
    const handleCancelSelection = useCallback(() => {

        onCancel?.();

        // Submit null coordinates to convey that the operation was cancelled
        socket.emit("pixel-coordinates-selected", {
            data: {
                u: null,
                v: null
            }
        });

        setSelectedPixels(null);
        setSelectedMarker(null);
        setImageDimensions(null);
        setImageSrc(null);
        setSubmitted(true);

    }, [onCancel]);

    // Handle submitting a pixel selection
    const handleSubmitPixels = useCallback(() => {

        if(!selectedPixels) return;

        const {u, v} = selectedPixels;

        onPixelSelection?.(u, v);

        socket.emit("pixel-coordinates-selected", {
            data: {
                u,
                v
            }
        });

        setSelectedPixels(null);
        setSelectedMarker(null);
        setImageDimensions(null);
        setImageSrc(null);
        setSubmitted(true);

    }, [onPixelSelection, selectedPixels]);


    // Effects
    // Initialise socket, or if the socket event to listen for changes, update the socket listener
    useEffect(() => {

        function handleImagePayload(payload: ImageSocketPayload){
            const imagePayload = payload.data.image;

            const blob = new Blob([imagePayload], { type: "image/jpeg" });
            setSelectedPixels(null);
            setSelectedMarker(null);
            setImageDimensions(null);
            setImageSrc(URL.createObjectURL(blob));
            setSubmitted(false);
        }

        socket.timeout(DEFAULT_TIMEOUT).emit('get-assessment-image', (err: Error, payload: ImageSocketPayload) => {
            if (err) {
                console.warn("Could not fetch current assessment image: Request timed out", err);
            }
            else {
                return handleImagePayload(payload);
            }
        });

        socket.on(socketEvent, handleImagePayload);

        return () => {
            socket.off(socketEvent);
        };
    }, [socketEvent]);

    // Load an image to apply image data to the canvas when the image source changes
    useEffect(() => {

        if (!imageSrc) {
            imageRef.current = null;
            return;
        }

        const image = new Image();

        image.onload = () => {
            imageRef.current = image;
            setImageDimensions({
                width: image.naturalWidth,
                height: image.naturalHeight
            });
            onImageLoad?.();
        };

        image.src = imageSrc;

        return () => {
            imageRef.current = null;
            image.onload = null;
            URL.revokeObjectURL(imageSrc);
        };
    }, [imageSrc, onImageLoad]);

    // Draw the image and selection marker if applicable
    useEffect(() => {

        if (!canvasRef.current || !imageRef.current || !imageDimensions) return;

        const canvas = canvasRef.current;
        const context = canvas.getContext("2d");

        if (!context) return;

        // Draw the image
        canvas.width = imageDimensions.width;
        canvas.height = imageDimensions.height;

        context.clearRect(0, 0, canvas.width, canvas.height);
        context.drawImage(imageRef.current, 0, 0, canvas.width, canvas.height);

        // Draw the selection marker
        if (!selectedMarker) return;

        const MARKER_RADIUS = 40;

        context.beginPath();
        context.arc(selectedMarker.u, selectedMarker.v, MARKER_RADIUS, 0, Math.PI * 2);
        context.fillStyle = "transparent";
        context.fill();
        context.lineWidth = 4;
        context.strokeStyle = "rgb(198, 44, 44)";
        context.stroke();
    }, [imageDimensions, selectedMarker]);


    // Render
    // noinspection MagicNumberJS
    return (
        <div className={"ImageCanvas"}>
            <AnimatePresence>
                {
                    !imageSrc && (
                                  <motion.div className={"ImageCanvas__background"}
                                              initial={{
                                                  opacity: 0
                                              }}
                                              animate={{
                                                  opacity: 1,
                                                  transition: {
                                                      delay: 0.5,
                                                      duration: 0.5
                                                  }
                                              }}
                                              exit={{
                                                  opacity: 0
                                              }}
                                              transition={{
                                                  delay: 0,
                                                  duration: 0.5
                                              }}
                                  >
                                      <img className={"size-40"} src={Logo} alt={"DragonFly Logo"}/>
                                      <motion.p
                                          layout
                                          layoutCrossfade={false}
                                          animate={shouldBlinkMissionStatus ? { opacity: [1, 1, 0, 0], transition: {
                                                  duration: 2,
                                                  times: [0, 0.75, 0.75, 1],
                                                  ease: "linear",
                                                  repeat: Infinity
                                              } } : { opacity: 1 }}
                                      >
                                          {missionStatus}
                                      </motion.p>
                                  </motion.div>
                              )
                }
            </AnimatePresence>
            <AnimatePresence>
                {
                    !!imageSrc && (
                                    <motion.div
                                        className={"ImageCanvas__image-container"}
                                        initial={{
                                            opacity: 0
                                        }}
                                        animate={{
                                            opacity: 1
                                        }}
                                        exit={{
                                            opacity: 0,
                                            transition: {
                                                delay: 0
                                            }
                                        }}
                                        transition={{
                                            delay: 0.5,
                                            duration: 0.2
                                        }}>
                                        <canvas
                                            ref={canvasRef}
                                            onClick={handlePixelSelection}
                                            className={"ImageCanvas__image"}
                                            width={imageDimensions?.width}
                                            height={imageDimensions?.height}
                                        />
                                        <form className={"ImageCanvas__form"} onSubmit={(e) => e.preventDefault()}>
                                            <Button onClick={handleCancelSelection}
                                                    disabled={submitted}
                                            >No Subject Found</Button>
                                            <KeyboardEffect showStartCursor={false}>Task: Select the target subject in the image</KeyboardEffect>
                                            <Button theme={"var(--color-active)"}
                                                    disabled={!selectedPixels || submitted}
                                                    onClick={handleSubmitPixels}>Send Subject Location</Button>
                                        </form>
                                    </motion.div>
                               )
                }
            </AnimatePresence>
        </div>
    );
}
