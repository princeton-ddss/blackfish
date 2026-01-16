import { useContext } from "react";
import { useServices } from "@/lib/loaders";
import { useSelectedService } from "@/lib/hooks";
import { ProfileContext } from "@/components/ProfileSelect";
import ServiceProvider from "@/providers/ServiceProvider";
import { assetPath } from "../config";
import PropTypes from "prop-types";

function Page({ task, children }) {
  const { profile } = useContext(ProfileContext);
  const { services, error, isLoading } = useServices(profile, task);
  const { selectedService, setSelectedServiceId } = useSelectedService(services);

  if (error) {
    return (
      <div className="flex flex-col flex-shrink-0 justify-center h-[calc(100vh-64px)]">
        <div className="flex flex-row justify-center items-center">
          <img
            className="h-16 w-auto mb-8"
            src={assetPath("/img/dead-fish.png")}
            alt="blackfish-error"
          />
        </div>
        <div className="flex flex-row justify-center items-center">
          {"There's something fishy going on here."}
        </div>
        <div className="flex flex-row justify-center items-center">
          {error.status}
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex flex-col flex-shrink-0 justify-center h-[calc(100vh-64px)]">
        <div className="flex flex-row justify-center items-center">
          <img
            className="animate-bounce h-16 w-auto mb-8"
            src={assetPath("/img/orca.png")}
            alt="blackfish-loading"
          />
        </div>
      </div>
    );
  }

  return (
    <div className="grid lg:grid-cols-[1fr_24rem] gap-12">
      <ServiceProvider
        selectedService={selectedService}
        setSelectedServiceId={setSelectedServiceId}
      >
        {children}
      </ServiceProvider>
    </div>
  );
}

Page.propTypes = {
  task: PropTypes.string,
  children: PropTypes.node,
};

export { Page };
