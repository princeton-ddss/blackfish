import { Transition } from "@headlessui/react";
import { CheckCircleIcon, XCircleIcon } from "@heroicons/react/24/outline";
import { XMarkIcon } from "@heroicons/react/20/solid";
import PropTypes from "prop-types";

/**
 * Notification component for transient success/error messages.
 *
 * @param {object} props
 * @param {boolean} props.show - Whether to show the notification
 * @param {"success" | "error"} props.variant - Notification type
 * @param {string} props.message - Main message text
 * @param {string} props.detail - Optional detail text
 * @param {function} props.onDismiss - Callback when dismissed
 */
function Notification({ show, variant = "success", message, detail, onDismiss }) {
  const config = {
    success: {
      Icon: CheckCircleIcon,
      iconColor: "text-green-400",
    },
    error: {
      Icon: XCircleIcon,
      iconColor: "text-red-400",
    },
  };

  const { Icon, iconColor } = config[variant];

  return (
    <div
      aria-live="assertive"
      className="pointer-events-none fixed inset-0 flex items-end px-4 py-6 sm:p-6 z-[100]"
    >
      <div className="flex w-full flex-col items-center space-y-4 sm:items-end">
        <Transition show={show}>
          <div className="pointer-events-auto w-full max-w-sm rounded-lg bg-white dark:bg-gray-800 shadow-lg dark:shadow-[0_0_30px_rgba(0,0,0,0.5)] ring-1 ring-gray-200 dark:ring-gray-600 transition data-[closed]:opacity-0 data-[enter]:transform data-[enter]:duration-300 data-[enter]:ease-out data-[closed]:data-[enter]:translate-y-2 data-[leave]:duration-100 data-[leave]:ease-in data-[closed]:data-[enter]:sm:translate-x-2 data-[closed]:data-[enter]:sm:translate-y-0">
            <div className="p-4">
              <div className="flex items-start">
                <div className="shrink-0">
                  <Icon aria-hidden="true" className={`size-6 ${iconColor}`} />
                </div>
                <div className="ml-3 w-0 flex-1 pt-0.5">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{message}</p>
                  {detail && (
                    <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{detail}</p>
                  )}
                </div>
                {onDismiss && (
                  <div className="ml-4 flex shrink-0">
                    <button
                      type="button"
                      onClick={onDismiss}
                      className="inline-flex rounded-md text-gray-400 hover:text-gray-600 dark:hover:text-white focus:outline-none"
                    >
                      <span className="sr-only">Close</span>
                      <XMarkIcon aria-hidden="true" className="size-5" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </div>
  );
}

Notification.propTypes = {
  show: PropTypes.bool.isRequired,
  variant: PropTypes.oneOf(["success", "error"]),
  message: PropTypes.string.isRequired,
  detail: PropTypes.string,
  onDismiss: PropTypes.func,
};

export default Notification;
