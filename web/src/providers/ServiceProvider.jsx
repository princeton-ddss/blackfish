import { createContext, useCallback, useRef } from 'react';
import PropTypes from "prop-types";

export const ServiceContext = createContext();

function ServiceProvider({ selectedService, setSelectedServiceId, children }) {
  // Registry of "cancel this in-flight request" callbacks, keyed by the id of
  // the service the request runs against. Lets a service action (e.g. Stop)
  // immediately abort requests for *that* service — not requests for another
  // service that merely happens to be selected — rather than waiting for its
  // status to poll to a terminal state. A Set per service tolerates multiple
  // concurrent requests against one service.
  const inFlightRef = useRef(new Map());

  const registerInFlight = useCallback((serviceId, cancel) => {
    const byService = inFlightRef.current;
    if (!byService.has(serviceId)) byService.set(serviceId, new Set());
    byService.get(serviceId).add(cancel);
    return () => {
      const set = byService.get(serviceId);
      if (!set) return;
      set.delete(cancel);
      if (set.size === 0) byService.delete(serviceId);
    };
  }, []);

  const cancelInFlight = useCallback((serviceId) => {
    const set = inFlightRef.current.get(serviceId);
    if (!set) return;
    for (const cancel of set) cancel();
    inFlightRef.current.delete(serviceId);
  }, []);

  return (
    <ServiceContext.Provider value={{
      selectedService, setSelectedServiceId, registerInFlight, cancelInFlight,
    }}>
      {children}
    </ServiceContext.Provider>
  );
};

ServiceProvider.propTypes = {
  selectedService: PropTypes.object,
  setSelectedServiceId: PropTypes.func,
  children: PropTypes.node,
};

export default ServiceProvider;
