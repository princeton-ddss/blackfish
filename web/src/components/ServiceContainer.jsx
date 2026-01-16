import { useContext } from "react";
import ServiceSelect from "./ServiceSelect";
import ServiceSummary from "./ServiceSummary";
import { ServiceContext } from "@/providers/ServiceProvider";
import PropTypes from "prop-types";

/**
 * Service Container component.
 * @param {object} options
 * @param {string} options.profile
 * @param {string} options.task
 * @param {JSX.Element} options.children
 * @return {JSX.Element}
 */
function ServiceContainer({
  profile,
  task,
  children
}) {

  const { selectedService } = useContext(ServiceContext);

  return (
    <div>
      <ServiceSelect
        profile={profile}
        task={task}
      />
      <ServiceSummary
        service={selectedService}
        profile={profile}
        task={task}
      />

      { children }

    </div>
  );
}

ServiceContainer.propTypes = {
  profile: PropTypes.string,
  task: PropTypes.string,
  children: PropTypes.node,
};

export default ServiceContainer;
