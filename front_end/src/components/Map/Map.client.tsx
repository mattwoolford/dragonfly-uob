import "leaflet/dist/leaflet.css";
import L from "leaflet";
import {useCallback, useEffect, useState} from "react";
import {MapContainer, Marker, TileLayer, useMapEvents} from "react-leaflet";
import DragonFlyLogo from "@assets/logo/emblem-svg/DragonFly Logo_Emblem.svg?raw";


// Define a type for geographical coordinates
type Coordinates = [number, number];


// Create a map pin to depict location
const LOCATION_PIN_ICON = L.divIcon({
    className: "",
    html: `
    <svg viewBox="0 0 2000 2000">
        <circle cx="1000" cy="1000" r="900" fill="var(--color-content-background)" fill-opacity="50" stroke="var(--color-highlight)" stroke-width="50"></circle>
        ${DragonFlyLogo}
    </svg>
    `,
    iconSize:   [50, 50],
    iconAnchor: [25, 25],
    popupAnchor:[0, -40],
});


// Define default coordinates
const DEFAULT_CENTER: Coordinates = [51.423967391658536, -2.67169820644399];


// Subcomponent to capture and handle map events
export function MapEvents(events: L.LeafletEventHandlerFnMap) {

    // Capture and handle map events
    useMapEvents(events);

    return null;

}


// Props for the map component
export interface MapProps {
    zoom?:       number;
    pin?:     Coordinates;
    onMapClick?: (lat: number, lng: number) => void;
}


export default function Map({ zoom = 10, pin: initialLocationPinPosition, onMapClick }: MapProps) {


    // State
    // Centre of the map
    const [center, _setCenter] = useState<Coordinates>(DEFAULT_CENTER);
    // Coordinates of the map marker
    const [locationPinPosition, setLocationPinPosition] = useState<Coordinates>(initialLocationPinPosition ?? DEFAULT_CENTER);


    // Callbacks
    // Handle map click
    const handleMapClick: L.LeafletMouseEventHandlerFn = useCallback((e) => {
        onMapClick?.(e.latlng.lat, e.latlng.lng);
    }, [onMapClick]);

    // Centre the map at a given location
    const setCenter = useCallback((coors: Coordinates, movePin: boolean = false) => {
        _setCenter(coors);
        if(movePin) {
            setLocationPinPosition(coors);
        }
    }, [setLocationPinPosition, _setCenter]);


    // Effects
    // Set the map's centre to the user's current location
    useEffect(() => {

        if (!navigator.geolocation) return;

        navigator.geolocation.getCurrentPosition(
            (pos) => setCenter([pos.coords.latitude, pos.coords.longitude]),
            () => { /* permission denied or unavailable — keep fallback */ },
        );

    }, [setCenter]);


    // Render
    return (
        <MapContainer center={center} zoom={zoom} className={"Map"}>
            <TileLayer
                attribution='&copy; <a href="https://stadiamaps.com/">Stadia Maps</a> &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png"
            />
            <MapEvents click={handleMapClick} />
            {initialLocationPinPosition && <Marker position={locationPinPosition} icon={LOCATION_PIN_ICON} />}
        </MapContainer>
    );
}
