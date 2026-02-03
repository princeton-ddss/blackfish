import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  XCircleIcon,
  XMarkIcon,
} from "@heroicons/react/20/solid";
import PropTypes from "prop-types";

/**
 * Alert color configuration for each variant.
 *
 * Color scheme:
 * - error: red - for failures, errors, destructive actions
 * - warning: yellow/amber - for cautions, potential issues
 * - success: green - for confirmations, completed actions
 * - info: blue - for neutral information, tips
 */
const variants = {
  error: {
    Icon: XCircleIcon,
    container: "bg-red-50 dark:bg-red-500/15",
    outline: "dark:outline dark:outline-red-500/25",
    border: "border-red-400 dark:border-red-500/25",
    iconColor: "text-red-400",
    title: "text-red-800 dark:text-red-200",
    text: "text-red-700 dark:text-red-200/80",
    dismiss: "text-red-500 hover:bg-red-100 dark:hover:bg-red-500/20 focus:ring-red-600",
  },
  warning: {
    Icon: ExclamationTriangleIcon,
    container: "bg-yellow-50 dark:bg-yellow-500/10",
    outline: "dark:outline dark:outline-yellow-500/15",
    border: "border-yellow-400 dark:border-yellow-500/15",
    iconColor: "text-yellow-400 dark:text-yellow-300",
    title: "text-yellow-800 dark:text-yellow-100",
    text: "text-yellow-700 dark:text-yellow-100/80",
    dismiss: "text-yellow-500 hover:bg-yellow-100 dark:hover:bg-yellow-500/20 focus:ring-yellow-600",
  },
  success: {
    Icon: CheckCircleIcon,
    container: "bg-green-50 dark:bg-green-500/15",
    outline: "dark:outline dark:outline-green-500/25",
    border: "border-green-400 dark:border-green-500/25",
    iconColor: "text-green-400",
    title: "text-green-800 dark:text-green-200",
    text: "text-green-700 dark:text-green-200/80",
    dismiss: "text-green-500 hover:bg-green-100 dark:hover:bg-green-500/20 focus:ring-green-600",
  },
  info: {
    Icon: InformationCircleIcon,
    container: "bg-blue-50 dark:bg-blue-500/15",
    outline: "dark:outline dark:outline-blue-500/25",
    border: "border-blue-400 dark:border-blue-500/25",
    iconColor: "text-blue-400",
    title: "text-blue-800 dark:text-blue-200",
    text: "text-blue-700 dark:text-blue-200/80",
    dismiss: "text-blue-500 hover:bg-blue-100 dark:hover:bg-blue-500/20 focus:ring-blue-600",
  },
};

/**
 * Alert component for displaying feedback messages.
 *
 * @param {object} props
 * @param {"error" | "warning" | "success" | "info"} props.variant - Alert type
 * @param {string} props.title - Optional bold title
 * @param {React.ReactNode} props.children - Alert content
 * @param {function} props.onDismiss - Optional dismiss callback (shows X button if provided)
 * @param {boolean} props.accent - Use left border accent style instead of rounded
 * @param {string} props.className - Additional CSS classes
 */
function Alert({
  variant = "info",
  title,
  children,
  onDismiss,
  accent = false,
  className = "",
}) {
  const config = variants[variant];
  const IconComponent = config.Icon;

  const containerClasses = accent
    ? `border-l-4 ${config.border} ${config.container} p-4 text-left`
    : `rounded-md ${config.container} ${config.outline} p-4 text-left`;

  return (
    <div className={`${containerClasses} ${className}`}>
      <div className="flex items-start">
        <div className="shrink-0">
          <IconComponent className={`size-5 ${config.iconColor}`} aria-hidden="true" />
        </div>
        <div className="ml-3">
          {title && (
            <h3 className={`text-sm font-medium ${config.title}`}>{title}</h3>
          )}
          <div className={`${title ? "mt-2" : ""} text-sm ${config.text}`}>
            {children}
          </div>
        </div>
        {onDismiss && (
          <div className="ml-auto pl-3">
            <button
              type="button"
              onClick={onDismiss}
              className={`inline-flex rounded-md focus:outline-none ${config.dismiss}`}
            >
              <span className="sr-only">Dismiss</span>
              <XMarkIcon className="size-5" aria-hidden="true" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

Alert.propTypes = {
  variant: PropTypes.oneOf(["error", "warning", "success", "info"]),
  title: PropTypes.string,
  children: PropTypes.node.isRequired,
  onDismiss: PropTypes.func,
  accent: PropTypes.bool,
  className: PropTypes.string,
};

export default Alert;
