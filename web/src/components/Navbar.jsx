import { useContext } from "react";
import { Link } from "react-router-dom";
import { Bars3Icon, SunIcon, MoonIcon, Cog6ToothIcon } from "@heroicons/react/24/outline";
import { ProfileContext } from "@/components/ProfileSelect";
import ProfileSelect from "@/components/ProfileSelect";
import ClusterStatusDropdown from "@/components/ClusterStatusDropdown";
import { useTheme } from "@/providers/ThemeProvider";
import { assetPath } from "@/config";
import PropTypes from "prop-types";

/**
 * Navbar component for consistent header across the app.
 * @param {object} props
 * @param {"dashboard" | "default"} props.variant - Layout variant
 * @param {boolean} props.showSidebar - Whether to show hamburger menu (mobile)
 * @param {function} props.onOpenSidebar - Callback for hamburger click
 */
function Navbar({ variant = "default", showSidebar = false, onOpenSidebar }) {
  const { profile, setProfile } = useContext(ProfileContext);
  const { isDark, toggleTheme } = useTheme();

  const isDashboard = variant === "dashboard";

  // Dashboard variant - single responsive header (same styling as desktop)
  if (isDashboard) {
    return (
      <div className="sticky top-0 z-50 flex h-12 items-center justify-between bg-white dark:bg-gray-900 pl-6 pr-4 border-b border-gray-200 dark:border-gray-700">
        <Link to="/dashboard" className="flex items-center gap-2">
          <img
            className="h-8 w-8 dark:drop-shadow-[0_0_8px_rgba(255,255,255,0.6)]"
            src={assetPath("/img/orca.png")}
            alt="blackfish"
          />
          <span className="text-2xl text-gray-900 dark:text-white font-medium leading-none pt-2 tracking-wider font-logo">Blackfish</span>
        </Link>
        <div className="flex items-center gap-4">
          <button
            onClick={toggleTheme}
            className="p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-gray-200"
            aria-label="Toggle theme"
          >
            {isDark ? (
              <SunIcon className="h-5 w-5" />
            ) : (
              <MoonIcon className="h-5 w-5" />
            )}
          </button>
          <ClusterStatusDropdown />
          <Link
            to="/settings"
            className="p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-gray-200"
            aria-label="Settings"
          >
            <Cog6ToothIcon className="h-5 w-5" />
          </Link>
          <a
            href="https://princeton-ddss.github.io/blackfish/latest"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-light text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-200"
          >
            Docs
          </a>
          <ProfileSelect
            selectedProfile={profile}
            setSelectedProfile={setProfile}
          />
        </div>
      </div>
    );
  }

  // Default variant - separate desktop and mobile headers
  return (
    <>
      {/* Desktop header */}
      <div className="hidden lg:fixed lg:inset-x-0 lg:top-0 lg:z-50 lg:flex lg:h-12 lg:items-center lg:justify-between lg:bg-white dark:lg:bg-gray-900 lg:pl-6 lg:pr-4 lg:border-b lg:border-gray-200 dark:lg:border-gray-700">
        <Link to="/dashboard" className="flex items-center gap-2">
          <img
            className="h-8 w-8 dark:drop-shadow-[0_0_8px_rgba(255,255,255,0.6)]"
            src={assetPath("/img/orca.png")}
            alt="blackfish"
          />
          <span className="text-2xl text-gray-900 dark:text-white font-medium leading-none pt-2 tracking-wider font-logo">Blackfish</span>
        </Link>
        <div className="flex items-center gap-4">
          <button
            onClick={toggleTheme}
            className="p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-gray-200"
            aria-label="Toggle theme"
          >
            {isDark ? (
              <SunIcon className="h-5 w-5" />
            ) : (
              <MoonIcon className="h-5 w-5" />
            )}
          </button>
          <ClusterStatusDropdown />
          <Link
            to="/settings"
            className="p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-gray-200"
            aria-label="Settings"
          >
            <Cog6ToothIcon className="h-5 w-5" />
          </Link>
          <a
            href="https://princeton-ddss.github.io/blackfish/latest"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-light text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-200"
          >
            Docs
          </a>
          <ProfileSelect
            selectedProfile={profile}
            setSelectedProfile={setProfile}
          />
        </div>
      </div>

      {/* Mobile header */}
      <div className="sticky top-0 z-40 flex h-12 items-center justify-between bg-white dark:bg-gray-900 px-4 border-b border-gray-200 dark:border-gray-700 sm:px-6 lg:hidden">
        {showSidebar && onOpenSidebar ? (
          <button
            type="button"
            onClick={onOpenSidebar}
            className="-m-2.5 p-2.5 text-gray-700 dark:text-gray-200 focus:outline-none"
          >
            <span className="sr-only">Open sidebar</span>
            <Bars3Icon aria-hidden="true" className="h-6 w-6" />
          </button>
        ) : (
          <div /> // Placeholder for layout
        )}
        <div className="flex items-center gap-3">
          <button
            onClick={toggleTheme}
            className="p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-gray-200"
            aria-label="Toggle theme"
          >
            {isDark ? (
              <SunIcon className="h-5 w-5" />
            ) : (
              <MoonIcon className="h-5 w-5" />
            )}
          </button>
          <ClusterStatusDropdown />
          <Link
            to="/settings"
            className="p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-gray-200"
            aria-label="Settings"
          >
            <Cog6ToothIcon className="h-5 w-5" />
          </Link>
          <a
            href="https://princeton-ddss.github.io/blackfish/latest"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-light text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-200"
          >
            Docs
          </a>
          <ProfileSelect
            selectedProfile={profile}
            setSelectedProfile={setProfile}
          />
        </div>
      </div>
    </>
  );
}

Navbar.propTypes = {
  variant: PropTypes.oneOf(["dashboard", "default"]),
  showSidebar: PropTypes.bool,
  onOpenSidebar: PropTypes.func,
};

export default Navbar;
