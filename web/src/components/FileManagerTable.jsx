import { useState } from "react";
import {
    ChevronLeftIcon,
    ChevronRightIcon,
    FolderIcon,
    DocumentIcon,
    ArrowPathIcon,
    TrashIcon,
    PhotoIcon,
    DocumentTextIcon,
    MusicalNoteIcon,
} from "@heroicons/react/24/outline";
import { assetPath } from "@/config";
import { fileSize, lastModified } from "@/lib/util";
import { getFileType } from "@/lib/fileApi";
import { isRootPath } from "@/lib/pathUtils";
import Pagination from "@/components/Pagination";
import PropTypes from "prop-types";

function getFileIcon(filename, isDir) {
    if (isDir) {
        return <FolderIcon className="h-6 w-6 text-gray-400" />;
    }

    const fileType = getFileType(filename);

    const iconConfig = {
        image: { Icon: PhotoIcon, className: "h-6 w-6 text-gray-400" },
        text: { Icon: DocumentTextIcon, className: "h-6 w-6 text-gray-400" },
        audio: { Icon: MusicalNoteIcon, className: "h-6 w-6 text-gray-400" },
    };

    if (fileType && iconConfig[fileType]) {
        const { Icon, className } = iconConfig[fileType];
        return <Icon className={className} />;
    }

    return <DocumentIcon className="h-6 w-6 text-gray-400" />;
}

function getFileTypeLabel(filename, isDir) {
    if (isDir) return "Folder";

    const fileType = getFileType(filename);
    if (!fileType) return "-";

    return fileType.charAt(0).toUpperCase() + fileType.slice(1);
}

function FileManagerTable({
    content,
    path,
    root,
    filesPerPage,
    query,
    setPath,
    isLoading,
    error,
    refresh,
    status,
    onFileClick,
    onDeleteClick,
    operationInProgress,
}) {
    const [currentPage, setCurrentPage] = useState(1);

    const indexOfLastFile = currentPage * filesPerPage;
    const indexOfFirstFile = indexOfLastFile - filesPerPage;

    const filteredContent = query === ""
        ? content
        : content?.filter((item) => item.name.toLowerCase().includes(query.toLowerCase()));

    const sortedContent = filteredContent ? [...filteredContent].sort((a, b) => {
        if (a.is_dir && !b.is_dir) return -1;
        if (!a.is_dir && b.is_dir) return 1;
        return new Date(b.modified_at) - new Date(a.modified_at);
    }) : [];

    const currentFiles = sortedContent.slice(indexOfFirstFile, indexOfLastFile);
    const isDisabled = status.disabled || operationInProgress;
    const showPlaceholderState = status.disabled || error || isLoading || content?.length === 0 || root === "";
    const heightClass = showPlaceholderState ? "h-[26rem]" : "max-h-[26rem]";

    return (
        <div
            id="file-manager-table"
            name="file-manager-table"
            className={`flex-none ${heightClass}`}
        >
            <div className="mt-3 flow-root">
                <div className="-my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
                    <div className="inline-block min-w-full py-2 align-middle sm:px-6 lg:px-8">
                        <div className={`ring-1 ring-gray-300 sm:rounded-lg ${heightClass} overflow-y-auto`}>
                            <table className="divide-y divide-gray-300 table-fixed w-full">
                                <thead>
                                    <tr>
                                        <th
                                            scope="col"
                                            className="sticky top-0 z-10 whitespace-nowrap py-4 text-left text-sm font-medium sm:pr-4 w-12 backdrop-blur bg-gray-50"
                                        >
                                            <button
                                                onClick={() => {
                                                    const parts = path.split("/").filter(p => p !== "");
                                                    if (parts.length <= 1) {
                                                        setPath(path === root || path.startsWith(root) ? root : "/");
                                                    } else {
                                                        setPath(parts.slice(0, -1).join("/"));
                                                    }
                                                }}
                                                disabled={isDisabled}
                                            >
                                                {path !== root && !isRootPath(path) && path !== `${root}/` && (
                                                    <ChevronLeftIcon className={`h-4 w-4 mt-1 ml-4 ${isDisabled ? "text-gray-300" : "text-gray-900 hover:text-gray-400"}`} />
                                                )}{" "}
                                            </button>
                                        </th>
                                        <th
                                            scope="col"
                                            className="sticky top-0 z-10 py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6 w-1/3 backdrop-blur bg-gray-50"
                                        >
                                            Name
                                        </th>
                                        <th
                                            scope="col"
                                            className="sticky top-0 z-10 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 w-[5rem] backdrop-blur bg-gray-50"
                                        >
                                            Type
                                        </th>
                                        <th
                                            scope="col"
                                            className="sticky top-0 z-10 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 w-[4.5rem] backdrop-blur bg-gray-50"
                                        >
                                            Size
                                        </th>
                                        <th
                                            scope="col"
                                            className="sticky top-0 z-10 px-3 py-3.5 text-left text-sm font-semibold text-gray-900 w-36 backdrop-blur bg-gray-50"
                                        >
                                            Last Modified
                                        </th>
                                        <th
                                            scope="col"
                                            className="sticky top-0 z-10 px-3 py-3.5 text-right text-sm font-semibold text-gray-900 w-12 backdrop-blur bg-gray-50"
                                        >
                                            <div className="flex gap-2 justify-end">
                                                <button
                                                    onClick={() => refresh()}
                                                    disabled={isDisabled}
                                                    title="Refresh"
                                                >
                                                    <ArrowPathIcon
                                                        className={`h-5 w-5 ${isDisabled ? "text-gray-300" : "text-gray-900 hover:text-gray-400"} ${isLoading ? "animate-spin" : ""}`}
                                                    />
                                                </button>
                                            </div>
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200 bg-white">
                                    {status.disabled ? (
                                        <tr>
                                            <td colSpan={6} className="h-64">
                                                <div className="font-light sm:text-sm text-center align-middle">
                                                    <img
                                                        className="h-16 ml-auto mr-auto opacity-80 mb-5"
                                                        height="56"
                                                        width="56"
                                                        src={assetPath("/img/dead-fish.png")}
                                                        alt="File manager disabled"
                                                    />
                                                    {status.detail || "Oops! Something went wrong."}
                                                </div>
                                            </td>
                                        </tr>
                                    ) : error ? (
                                        <tr>
                                            <td colSpan={6} className="h-64">
                                                <div className="font-light sm:text-sm text-center align-middle">
                                                    <img
                                                        className="h-16 ml-auto mr-auto opacity-80 mb-5"
                                                        height="56"
                                                        width="56"
                                                        src={assetPath("/img/dead-fish.png")}
                                                        alt="Loading error."
                                                    />
                                                    Oops! There seems to be a problem here...
                                                </div>
                                            </td>
                                        </tr>
                                    ) : isLoading ? (
                                        <>
                                            {Array.from({ length: 5 }).map((_, i) => (
                                                <tr key={i}>
                                                    <td colSpan={6} className="relative whitespace-nowrap py-3 px-5 animate-pulse">
                                                        <div className="bg-gray-100 h-9 rounded-md"></div>
                                                    </td>
                                                </tr>
                                            ))}
                                        </>
                                    ) : content?.length === 0 ? (
                                        <tr>
                                            <td colSpan={6} className="h-64">
                                                <div className="font-light sm:text-sm text-center align-middle">
                                                    <img
                                                        className="h-16 ml-auto mr-auto opacity-80 mb-5"
                                                        height="56"
                                                        width="56"
                                                        src={assetPath("/img/question-mark.png")}
                                                        alt="No files found."
                                                    />
                                                    {"Hmm. There don't seem to be any files here..."}
                                                </div>
                                            </td>
                                        </tr>
                                    ) : root === "" ? (
                                        <tr>
                                            <td colSpan={6} className="h-64">
                                                <div className="font-light sm:text-sm text-center align-middle">
                                                    {"No service selected."}
                                                </div>
                                            </td>
                                        </tr>
                                    ) : (
                                        currentFiles.map((item) => (
                                            <tr
                                                key={item.path}
                                                className={`bg-white hover:bg-gray-50 ${onFileClick && !item.is_dir ? 'cursor-pointer' : ''}`}
                                                onClick={() => onFileClick && !item.is_dir && onFileClick(item)}
                                            >
                                                <td className="relative whitespace-nowrap w-12 py-3 px-3 text-gray-700 text-left text-sm font-medium">
                                                    <div className="flex">
                                                        {getFileIcon(item.name, item.is_dir)}
                                                    </div>
                                                </td>
                                                <td className="whitespace-nowrap w-1/4 py-3 pl-4 pr-3 text-left text-sm text-gray-900">
                                                    <div className="overflow-x-scroll">{item.name}</div>
                                                </td>
                                                <td className="whitespace-nowrap w-[5rem] py-3 px-3 text-left text-sm text-gray-600">
                                                    {getFileTypeLabel(item.name, item.is_dir) === "-" ? (
                                                        <span>-</span>
                                                    ) : (
                                                        <span className="inline-flex items-center rounded-md bg-gray-50 px-2 py-1 text-xs font-medium text-gray-600 ring-1 ring-inset ring-gray-500/10">
                                                            {getFileTypeLabel(item.name, item.is_dir)}
                                                        </span>
                                                    )}
                                                </td>
                                                <td className="whitespace-nowrap w-[4.5rem] py-3 px-3 text-left text-sm text-gray-900">
                                                    <div className="flex">
                                                        {item.is_dir ? "-" : fileSize(item.size)}
                                                    </div>
                                                </td>
                                                <td className="whitespace-nowrap w-36 py-3 px-3 text-left text-sm text-gray-900">
                                                    <div className="flex">
                                                        {lastModified(item.modified_at)}
                                                    </div>
                                                </td>
                                                <td className="whitespace-nowrap w-12 py-3 px-3 text-right">
                                                    <div className="flex gap-2 justify-end">
                                                        {item.is_dir ? (
                                                            <button
                                                                onClick={() => {
                                                                    if (!isDisabled) {
                                                                        setPath(item.path);
                                                                    }
                                                                }}
                                                                disabled={isDisabled}
                                                                className={`${isDisabled ? "text-gray-300" : "text-gray-900"}`}
                                                            >
                                                                <ChevronRightIcon className="h-4 w-4 hover:text-gray-400" />
                                                            </button>
                                                        ) : (
                                                            onDeleteClick && (
                                                                <button
                                                                    onClick={(e) => {
                                                                        e.stopPropagation();
                                                                        onDeleteClick(item);
                                                                    }}
                                                                    disabled={isDisabled}
                                                                    className={`${isDisabled ? "text-gray-200" : "text-gray-400 hover:text-red-500"}`}
                                                                    title="Delete file"
                                                                >
                                                                    <TrashIcon className="h-5 w-5" />
                                                                </button>
                                                            )
                                                        )}
                                                    </div>
                                                </td>
                                            </tr>
                                        ))
                                    )}
                                    <tr className="bg-white">
                                        <td className="whitespace-nowrap h-16"></td>
                                        <td className="whitespace-nowrap h-16"></td>
                                        <td className="whitespace-nowrap h-16"></td>
                                        <td className="whitespace-nowrap h-16"></td>
                                        <td className="whitespace-nowrap h-16"></td>
                                        <td className="whitespace-nowrap h-16"></td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            <Pagination
                filesPerPage={filesPerPage}
                totalFiles={sortedContent.length}
                currentPage={currentPage}
                setCurrentPage={setCurrentPage}
                disabled={isDisabled}
            />
        </div>
    );
}

FileManagerTable.propTypes = {
    content: PropTypes.array,
    path: PropTypes.string,
    root: PropTypes.string,
    filesPerPage: PropTypes.number,
    query: PropTypes.string,
    setPath: PropTypes.func,
    isLoading: PropTypes.bool,
    error: PropTypes.object,
    refresh: PropTypes.func,
    status: PropTypes.object,
    onFileClick: PropTypes.func,
    onDeleteClick: PropTypes.func,
    operationInProgress: PropTypes.bool,
};

export default FileManagerTable;
