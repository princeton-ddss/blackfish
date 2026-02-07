import { createContext } from 'react';
import PropTypes from "prop-types";

export const ServiceContext = createContext();

function ServiceProvider({ selectedService, setSelectedServiceId, children }) {

  return (
    <ServiceContext.Provider value={{
      selectedService, setSelectedServiceId
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
