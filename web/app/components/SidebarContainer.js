import { useContext } from "react";
import { ProfileContext } from "./ProfileSelect";

import ProfileSelect from "@/app/components/ProfileSelect";
import ServiceContainer from "@/app/components/ServiceContainer";
import ServiceLauncher from "@/app/components/ServiceLauncher";
import PropTypes from "prop-types";

/**
 * Sidebar Container component.
 * @param {object} options
 * @param {string} options.task
 * @param {object} options.defaultContainerOptions
 * @param {string} options.defaultContainerOptions.input_dir
 * @param {boolean} options.defaultContainerOptions.disable_custom_kernels
 * @param {JSX.Element} options.ContainerOptionsFormComponent
 * @param {JSX.Element} options.children
 * @return {JSX.Element}
 */
function SidebarContainer({
  task,
  defaultContainerOptions,
  ContainerOptionsFormComponent,
  bgColor = 'white',
  children
}) {
  const { profile, setProfile } = useContext(ProfileContext);

  return (
    <div className={`bg-${bgColor} flex flex-col lg:w-96 lg:p-8 lg:pr-12`}>
      <ProfileSelect
        selectedProfile={profile}
        setSelectedProfile={setProfile}
      />

      <ServiceContainer
        profile={profile}
        task={task}
      >
        <ServiceLauncher
          profile={profile}
          task={task}
          defaultContainerOptions={defaultContainerOptions}
          ContainerOptionsFormComponent={ContainerOptionsFormComponent}
        />
      </ServiceContainer>

      {children}

    </div>
  );
}

SidebarContainer.propTypes = {
  task: PropTypes.string,
  defaultContainerOptions: PropTypes.shape({
    input_dir: PropTypes.string,
    disable_custom_kernels: PropTypes.bool,
  }),
  ContainerOptionsFormComponent: PropTypes.elementType,
  children: PropTypes.node,
  bgColor: PropTypes.string,
};

export { SidebarContainer };
