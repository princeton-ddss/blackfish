import PropTypes from "prop-types";

function StatusBadge({ status, errored = 0 }) {
    const getStatusConfig = () => {
        switch (status) {
            case "running":
                return errored > 0 ? {
                    bg: "bg-yellow-50 dark:bg-yellow-900/30",
                    text: "text-yellow-700 dark:text-yellow-400",
                    ring: "ring-yellow-600/20 dark:ring-yellow-500/30",
                    label: "Running",
                } : {
                    bg: "bg-green-50 dark:bg-green-900/30",
                    text: "text-green-700 dark:text-green-400",
                    ring: "ring-green-600/20 dark:ring-green-500/30",
                    label: "Running",
                };
            case "broken":
                return {
                    bg: "bg-orange-50 dark:bg-orange-900/30",
                    text: "text-orange-700 dark:text-orange-400",
                    ring: "ring-orange-600/20 dark:ring-orange-500/30",
                    label: "Broken",
                };
            case "stopped":
            default:
                return {
                    bg: "bg-gray-50 dark:bg-gray-700",
                    text: "text-gray-600 dark:text-gray-400",
                    ring: "ring-gray-500/10 dark:ring-gray-600",
                    label: "Stopped",
                };
        }
    };

    const config = getStatusConfig();

    return (
        <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${config.bg} ${config.text} ${config.ring}`}>
            {config.label}
        </span>
    );
}

StatusBadge.propTypes = {
    status: PropTypes.string.isRequired,
    errored: PropTypes.number,
};

export default StatusBadge;
