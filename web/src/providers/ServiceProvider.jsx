import { createContext, useCallback, useRef } from 'react';
import PropTypes from "prop-types";

export const ServiceContext = createContext();

function ServiceProvider({ selectedService, setSelectedServiceId, children }) {
  // Registry of "cancel this in-flight request" callbacks. Lets a service
  // action (e.g. Stop) immediately abort any request against that service,
  // rather than waiting for its status to poll to a terminal state.
  const inFlightRef = useRef(new Set());

  const registerInFlight = useCallback((cancel) => {
    inFlightRef.current.add(cancel);
    return () => inFlightRef.current.delete(cancel);
  }, []);

  const cancelInFlight = useCallback(() => {
    for (const cancel of inFlightRef.current) cancel();
    inFlightRef.current.clear();
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
