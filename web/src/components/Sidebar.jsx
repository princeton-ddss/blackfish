import { useContext } from "react";
import { Link, useLocation } from "react-router";
import {
    ChatBubbleLeftRightIcon,
    ChatBubbleLeftEllipsisIcon,
    MicrophoneIcon,
    FolderIcon,
    HomeIcon,
    CubeIcon,
    Square3Stack3DIcon,
} from "@heroicons/react/24/outline";
import { assetPath } from "@/config";
import { ProfileContext } from "@/components/ProfileSelect";
import PropTypes from "prop-types";

const navigation = [
    { name: "Dashboard", href: "/dashboard", icon: HomeIcon },
    { name: "Jobs", href: "/jobs", icon: Square3Stack3DIcon, slurmOnly: true },
    { name: "Models", href: "/models", icon: CubeIcon },
    { name: "Files", href: "/file-manager", icon: FolderIcon },
];

const secondaryNavigation = [
    { name: "Text Generation", href: "/text-generation", icon: ChatBubbleLeftRightIcon },
    { name: "Speech Recognition", href: "/speech-recognition", icon: MicrophoneIcon },
];

function classNames(...classes) {
    return classes.filter(Boolean).join(" ");
}

function Sidebar({ collapsed = false }) {
    const location = useLocation();
    const pathname = location.pathname;
    const { profile } = useContext(ProfileContext);
    const isSlurm = profile?.schema === "slurm";

    const isCurrent = (href) => pathname === href || pathname.startsWith(href + "/");
    const isDisabled = (item) => item.slurmOnly && !isSlurm;

    const renderItem = (item) => {
        const current = isCurrent(item.href);
        const disabled = isDisabled(item);
        const iconClasses = classNames(
            current
                ? "text-gray-900 dark:text-white"
                : "text-gray-700 group-hover:text-gray-400 dark:text-gray-200 dark:group-hover:text-white",
            "h-6 w-6 shrink-0"
        );
        const rowClasses = classNames(
            "group flex items-center gap-x-3 rounded-md p-2 text-sm",
            collapsed && "justify-center"
        );

        if (disabled) {
            return (
                <span
                    className={classNames(
                        rowClasses,
                        "text-gray-400 dark:text-white/50 cursor-not-allowed"
                    )}
                    title={collapsed ? `${item.name} — requires Slurm profile` : "Requires Slurm profile"}
                >
                    <item.icon
                        aria-hidden="true"
                        className="h-6 w-6 shrink-0 text-gray-400 dark:text-white/50"
                    />
                    {!collapsed && item.name}
                </span>
            );
        }

        return (
            <Link
                to={item.href}
                title={collapsed ? item.name : undefined}
                className={classNames(
                    current
                        ? "bg-gray-100 dark:bg-white/10 text-gray-900 dark:text-white font-medium"
                        : "text-gray-700 dark:text-gray-200 font-normal hover:text-gray-400 dark:hover:text-white",
                    rowClasses
                )}
            >
                <item.icon aria-hidden="true" className={iconClasses} />
                {!collapsed && item.name}
            </Link>
        );
    };

    return (
        <div
            className={classNames(
                "flex grow flex-col gap-y-5 overflow-y-auto overflow-x-hidden border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-blue-500 pt-4",
                collapsed ? "px-2" : "pl-6 pr-4"
            )}
        >
            {/* Logo header - orca mark, aligned with the nav icons below */}
            <div className="-mx-2 shrink-0">
                <Link
                    to="/dashboard"
                    className={classNames(
                        "flex items-center p-2",
                        collapsed ? "justify-center" : "pl-1"
                    )}
                >
                    <img
                        className="h-10 w-10 shrink-0 dark:drop-shadow-[0_0_8px_rgba(255,255,255,0.6)]"
                        src={assetPath("/img/orca.png")}
                        alt="blackfish"
                    />
                </Link>
            </div>
            <nav className="flex flex-1 flex-col">
                <ul role="list" className="flex flex-1 flex-col gap-y-7 pt-4">
                    <li>
                        <ul role="list" className="-mx-2 space-y-1">
                            {navigation.map((item) => (
                                <li key={item.name}>{renderItem(item)}</li>
                            ))}
                        </ul>
                    </li>
                    <li>
                        {!collapsed && (
                            <div className="text-xs font-semibold text-gray-400 dark:text-gray-100">Services</div>
                        )}
                        <ul role="list" className={classNames("-mx-2 space-y-1", !collapsed && "mt-2")}>
                            {secondaryNavigation.map((item) => (
                                <li key={item.name}>{renderItem(item)}</li>
                            ))}
                        </ul>
                    </li>
                    <li className={classNames("mt-auto", collapsed ? "-mx-2" : "-ml-6 -mr-4")}>
                        <a
                            href="https://github.com/princeton-ddss/blackfish/issues"
                            target="_blank"
                            rel="noopener noreferrer"
                            title={collapsed ? "Feedback" : undefined}
                            className={classNames(
                                "group flex items-center gap-x-3 py-3 text-sm font-normal text-gray-700 dark:text-gray-200 hover:text-gray-400 dark:hover:text-white",
                                collapsed ? "justify-center px-2" : "pl-6 pr-4"
                            )}
                        >
                            <ChatBubbleLeftEllipsisIcon className="h-6 w-6 shrink-0 text-gray-400 dark:text-gray-200 group-hover:text-gray-300 dark:group-hover:text-white" aria-hidden="true" />
                            {!collapsed && "Feedback"}
                        </a>
                    </li>
                </ul>
            </nav>
        </div>
    );
}

Sidebar.propTypes = {
    collapsed: PropTypes.bool,
};

export default Sidebar;
