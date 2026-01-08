"use client";

import { createContext, useState, useEffect } from "react";
import {
  Label,
  Listbox,
  ListboxButton,
  ListboxOption,
  ListboxOptions
} from "@headlessui/react";
import { CheckIcon, ChevronUpDownIcon } from "@heroicons/react/20/solid";
import { useProfiles } from "@/app/lib/loaders";
import { ExclamationTriangleIcon } from "@heroicons/react/24/solid";
import PropTypes from "prop-types";

const ProfileContext = createContext();

/**
 * Profile provider component.
 * @param {object} options
 * @param {JSX.Element} options.children
 * @return {JSX.Element}
 */
const ProfileProvider = ({ children }) => {
  const [profile, setProfileContext] = useState(null);

  useEffect(() => {
    const data = localStorage.getItem("profile");
    const restoredProfile = data ? JSON.parse(data) : null;
    console.debug("Restored profile", restoredProfile);
    setProfileContext(restoredProfile);
  }, []);

  const setProfile = (profile) => {
    localStorage.setItem("profile", JSON.stringify(profile));
    setProfileContext(profile);
  };

  return (
    <ProfileContext.Provider value={{ profile, setProfile }}>
      {children}
    </ProfileContext.Provider>
  );
}

ProfileProvider.propTypes = {
  children: PropTypes.node
};


/**
 * Profile Select component.
 * @param {object} options
 * @param {object} options.selectedProfile
 * @param {Function} options.setSelectedProfile
 * @return {JSX.Element}
 */
function ProfileSelect({
  selectedProfile,
  setSelectedProfile
}) {
  const { profiles, error, isLoading } = useProfiles();

  if (isLoading) {
    return <div>Loading profiles...</div>;
  }

  if (error) {
    return <div>Error!</div>;
  }

  if (profiles.length === 0) {
    return <div>No profiles found.</div>;
  }

  return (
    <Listbox value={selectedProfile} onChange={setSelectedProfile}>
      <Label className="mt-2 block text-sm font-medium leading-6 text-gray-900">
        Profile
      </Label>
      {
        selectedProfile && !profiles.map(x => x.name).includes(selectedProfile.name) &&
        <div>
          {/* TODO: add Alert */}
          Profile is missing.
        </div>
      }
      <div className="relative mt-2 mb-2">
        {
          selectedProfile
            ? <ListboxButton
                className="relative w-full cursor-default rounded-md bg-white py-1.5 pl-1 pr-10 text-left text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm sm:leading-6"
              >
              <span className="flex items-center">
                <span className="ml-3 block truncate">
                  {selectedProfile.name ? selectedProfile.name : ""}
                </span>
                <span className="ml-2 text-slate-400 text-sm font-light">
                  @{selectedProfile.host ? selectedProfile.host : "localhost"}
                </span>
                <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                  <ChevronUpDownIcon
                    className="h-5 w-5 text-gray-400"
                    aria-hidden="true"
                  />
                </span>
              </span>
            </ListboxButton>
            : <ListboxButton
                className="relative w-full cursor-default rounded-md bg-white py-1.5 pl-1 pr-10 text-left text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm sm:leading-6"
              >
              <span className="flex items-center">
                <span className="pointer-events-none flex-shrink-0 pl-3">
                  <ExclamationTriangleIcon
                    className="h-5 w-5 text-yellow-400"
                    aria-hidden="true"
                  />
                </span>
                <span className="ml-3 block truncate">
                  {"No profile selected"}
                </span>
                <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                  <ChevronUpDownIcon
                    className="h-5 w-5 text-gray-400"
                    aria-hidden="true"
                  />
                </span>
              </span>
            </ListboxButton>
        }

        <ListboxOptions
          className="absolute z-10 mt-1 max-h-60 overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm w-[var(--button-width)]"
          anchor="bottom"
        >
          {profiles.map((profile) => (
            <ListboxOption
              key={profile.name}
              value={profile}
              className="group flex gap-2 bg-white data-[focus]:bg-blue-500 data-[focus]:text-white relative cursor-default select-none py-2 pl-1 pr-9 text-gray-900"
            >
              <div className="flex">
                <span className="ml-3 block truncate font-normal data-[selected]:font-semibold">
                  {profile.name}
                </span>
              </div>
              <span className="ml-1 text-slate-400 text-sm font-light data-[selected]:text-gray-100">
                @{profile.host ? profile.host : "localhost"}
              </span>
              <span className="invisible group-data-[selected]:visible absolute inset-y-0 right-0 flex items-center pr-4 group-data-[focus]:text-white text-blue-600">
                <CheckIcon className="size-5" />
              </span>
            </ListboxOption>
          ))}
        </ListboxOptions>
      </div>
    </Listbox>
  )
}

ProfileSelect.propTypes = {
  selectedProfile: PropTypes.object,
  setSelectedProfile: PropTypes.func
};

export default ProfileSelect;
export { ProfileContext, ProfileProvider };
