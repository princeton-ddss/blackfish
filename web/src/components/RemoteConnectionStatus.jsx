import { ArrowPathIcon } from "@heroicons/react/24/outline";
import { isRemoteProfile } from "@/lib/util";
import PropTypes from "prop-types";

/**
 * Connection-status indicator for a remote (SFTP) profile: a colored dot, a
 * "Connected to user@host" / "Disconnected" / "Connecting..." label, and an
 * optional reconnect button. Renders nothing for local profiles, so callers
 * can drop it in unconditionally.
 *
 * @param {object} options
 * @param {object} options.profile - The active profile ({ user, host, ... }).
 * @param {boolean} options.isConnected - Whether the SFTP session is up.
 * @param {boolean} options.isConnecting - Whether a (re)connect is in flight.
 * @param {object} options.connectionError - Truthy when the connection failed.
 * @param {Function} [options.onReconnect] - If given, a reconnect button shows
 *   when disconnected; omit to render no button.
 * @param {"sm"|"xs"} [options.size="sm"] - Text/icon scale.
 * @return {JSX.Element|null}
 */
function RemoteConnectionStatus({
  profile,
  isConnected,
  isConnecting,
  connectionError,
  onReconnect = null,
  size = "sm",
}) {
  if (!isRemoteProfile(profile)) {
    return null;
  }

  const textClass = size === "xs" ? "text-xs" : "text-sm";
  const iconClass = size === "xs" ? "h-3.5 w-3.5" : "h-4 w-4";

  return (
    <div className="flex items-center gap-1.5">
      <span
        className={`inline-block h-2 w-2 flex-shrink-0 rounded-full ${
          isConnected
            ? "bg-green-500"
            : connectionError
              ? "bg-red-500"
              : "animate-pulse bg-yellow-500"
        }`}
      />
      <span className={`${textClass} text-gray-600 dark:text-gray-400`}>
        {isConnected
          ? `Connected to ${profile.user}@${profile.host}`
          : connectionError
            ? "Disconnected"
            : "Connecting..."}
      </span>
      {onReconnect && connectionError && (
        <button
          onClick={onReconnect}
          disabled={isConnecting}
          className="ml-1 p-0.5 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 disabled:opacity-50 focus:outline-none"
          aria-label="Reconnect"
        >
          <ArrowPathIcon className={`${iconClass} ${isConnecting ? "animate-spin" : ""}`} />
        </button>
      )}
    </div>
  );
}

RemoteConnectionStatus.propTypes = {
  profile: PropTypes.object,
  isConnected: PropTypes.bool,
  isConnecting: PropTypes.bool,
  connectionError: PropTypes.object,
  onReconnect: PropTypes.func,
  size: PropTypes.oneOf(["sm", "xs"]),
};

export default RemoteConnectionStatus;
