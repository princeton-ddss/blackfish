import { useContext } from "react";
import { ProfileContext } from "./ProfileSelect";
import ServiceContainer from "@/components/ServiceContainer";
import PropTypes from "prop-types";

/**
 * System Message Input component for sidebar.
 * @param {object} options
 * @param {object} options.message
 * @param {Function} options.onChange
 * @return {JSX.Element}
 */
function SystemMessageInput({ message, onChange }) {
  return (
    <div className="mt-6">
      <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
        System Message
      </label>
      <textarea
        placeholder="You are a helpful assistant."
        rows={10}
        value={message?.content || ""}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg bg-white dark:bg-gray-700 resize-none px-3 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 border border-gray-300 dark:border-gray-600 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
      />
    </div>
  );
}

SystemMessageInput.propTypes = {
  message: PropTypes.object,
  onChange: PropTypes.func,
};

/**
 * Sidebar Container component.
 * @param {object} options
 * @param {string} options.task
 * @param {object} options.defaultContainerOptions
 * @param {string} options.defaultContainerOptions.input_dir
 * @param {boolean} options.defaultContainerOptions.disable_custom_kernels
 * @param {JSX.Element} options.ContainerOptionsFormComponent
 * @param {JSX.Element} options.ParametersFormComponent
 * @param {object} options.parametersFormProps
 * @param {object} options.systemMessage
 * @param {Function} options.onSystemMessageChange
 * @return {JSX.Element}
 */
function SidebarContainer({
  task,
  defaultContainerOptions,
  ContainerOptionsFormComponent,
  ParametersFormComponent,
  parametersFormProps,
  systemMessage,
  onSystemMessageChange,
  bgColor = 'white',
}) {
  const { profile } = useContext(ProfileContext);

  return (
    <div className={`bg-${bgColor} dark:bg-gray-800 flex flex-col lg:w-96 lg:pt-2 lg:pb-8 lg:pl-8 lg:pr-8`}>
      <ServiceContainer
        profile={profile}
        task={task}
        defaultContainerOptions={defaultContainerOptions}
        ContainerOptionsFormComponent={ContainerOptionsFormComponent}
        ParametersFormComponent={ParametersFormComponent}
        parametersFormProps={parametersFormProps}
      />

      {systemMessage && onSystemMessageChange && (
        <SystemMessageInput
          message={systemMessage}
          onChange={onSystemMessageChange}
        />
      )}
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
  ParametersFormComponent: PropTypes.elementType,
  parametersFormProps: PropTypes.object,
  systemMessage: PropTypes.object,
  onSystemMessageChange: PropTypes.func,
  bgColor: PropTypes.string,
};

export { SidebarContainer };
