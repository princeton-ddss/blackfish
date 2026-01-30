import { Link, useLocation } from "react-router-dom";
import {
    ChatBubbleLeftRightIcon,
    ChatBubbleLeftEllipsisIcon,
    MicrophoneIcon,
    FolderIcon,
    HomeIcon,
    CubeIcon,
    ViewfinderCircleIcon,
    Square3Stack3DIcon,
} from "@heroicons/react/24/outline";
import { assetPath } from "@/config";

const navigation = [
    { name: "Dashboard", href: "/dashboard", icon: HomeIcon },
    { name: "Jobs", href: "/jobs", icon: Square3Stack3DIcon },
    { name: "Models", href: "/models", icon: CubeIcon },
    { name: "Files", href: "/file-manager", icon: FolderIcon },
];

const secondaryNavigation = [
    { name: "Text Generation", href: "/text-generation", icon: ChatBubbleLeftRightIcon },
    { name: "Speech Recognition", href: "/speech-recognition", icon: MicrophoneIcon },
    { name: "Object Detection", href: "/object-detection", icon: ViewfinderCircleIcon },
];

function classNames(...classes) {
    return classes.filter(Boolean).join(" ");
}

function Sidebar() {
    const location = useLocation();
    const pathname = location.pathname;

    const isCurrent = (href) => pathname === href || pathname.startsWith(href + "/");

    return (
        <div className="flex grow flex-col gap-y-5 overflow-y-auto border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-blue-500 pl-6 pr-4 pt-4">
            {/* Logo - only visible in mobile drawer */}
            <div className="flex h-12 shrink-0 items-center lg:hidden">
                <Link to="/dashboard" className="flex items-center gap-2">
                    <img
                        className="h-8 w-8 dark:drop-shadow-[0_0_8px_rgba(255,255,255,0.6)]"
                        src={assetPath("/img/orca.png")}
                        alt="blackfish"
                    />
                    <span className="text-2xl text-gray-900 dark:text-white font-semibold leading-none pt-2 tracking-wider font-logo">Blackfish</span>
                </Link>
            </div>
            <nav className="flex flex-1 flex-col">
                <ul role="list" className="flex flex-1 flex-col gap-y-7 pt-4">
                    <li>
                        <ul role="list" className="-mx-2 space-y-1">
                            {navigation.map((item) => (
                                <li key={item.name}>
                                    <Link
                                        to={item.href}
                                        className={classNames(
                                            isCurrent(item.href)
                                                ? "text-gray-900 dark:text-white font-medium"
                                                : "text-gray-700 dark:text-gray-200 font-normal hover:text-gray-400 dark:hover:text-white",
                                            "group flex gap-x-3 rounded-md p-2 text-sm"
                                        )}
                                    >
                                        <item.icon
                                            aria-hidden="true"
                                            className={classNames(
                                                isCurrent(item.href)
                                                    ? "text-gray-900 dark:text-white"
                                                    : "text-gray-400 group-hover:text-gray-300 dark:text-gray-200 dark:group-hover:text-white",
                                                "h-6 w-6 shrink-0"
                                            )}
                                        />
                                        {item.name}
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    </li>
                    <li>
                        <div className="text-xs font-semibold text-gray-400 dark:text-gray-100">Services</div>
                        <ul role="list" className="-mx-2 mt-2 space-y-1">
                            {secondaryNavigation.map((item) => (
                                <li key={item.name}>
                                    <Link
                                        to={item.href}
                                        className={classNames(
                                            isCurrent(item.href)
                                                ? "text-gray-900 dark:text-white font-normal"
                                                : "text-gray-700 dark:text-gray-200 font-normal hover:text-gray-400 dark:hover:text-gray-100",
                                            "group flex gap-x-3 rounded-md p-2 text-sm"
                                        )}
                                    >
                                        <item.icon
                                            aria-hidden="true"
                                            className={classNames(
                                                isCurrent(item.href) ? "text-gray-900 dark:text-white" : "text-gray-400 dark:text-gray-200 group-hover:text-gray-100",
                                                "h-6 w-6 shrink-0"
                                            )}
                                        />
                                        {item.name}
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    </li>
                    <li className="-ml-6 -mr-4 mt-auto">
                        <a
                            href="https://github.com/princeton-ddss/blackfish/issues"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="group flex items-center gap-x-3 pl-6 pr-4 py-3 text-sm font-normal text-gray-700 dark:text-gray-200 hover:text-gray-400 dark:hover:text-white"
                        >
                            <ChatBubbleLeftEllipsisIcon className="h-6 w-6 text-gray-400 dark:text-gray-200 group-hover:text-gray-300 dark:group-hover:text-white" aria-hidden="true" />
                            Feedback
                        </a>
                    </li>
                </ul>
            </nav>
        </div>
    );
}

export default Sidebar;
