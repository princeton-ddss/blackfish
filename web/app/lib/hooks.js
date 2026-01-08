import { useState, useEffect } from "react";

export function useSelectedService(services) {
    const [selectedServiceId, setSelectedServiceId] = useState(null);
    const selectedService = services?.find((service) => service.id === selectedServiceId) ?? null;

    useEffect(() => {
        if (!services || services.length === 0) {
            setSelectedServiceId(null);
        } else if (!selectedService) {
            setSelectedServiceId(services[0].id);
        }
    }, [services, selectedService]);

    return { selectedService, setSelectedServiceId };
}
