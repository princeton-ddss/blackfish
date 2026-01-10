import PropTypes from "prop-types";

/**
 * Task Container component.
 * @param {object} options
 * @param {JSX.Element} options.children
 * @return {JSX.Element}
 */
function TaskContainer({ children }) {
  return (
    <div className="bg-white">
      {children}
    </div>
  );
}

TaskContainer.propTypes = {
  children: PropTypes.node,
};

export { TaskContainer };
