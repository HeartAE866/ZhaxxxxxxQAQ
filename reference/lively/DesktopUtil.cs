using System;
using Lively.Common.Helpers.Pinvoke;

namespace Lively.Common.Helpers.Shell
{
    public static class DesktopUtil
    {
        public static bool GetDesktopIconVisibility()
        {
            NativeMethods.SHELLSTATE state = new NativeMethods.SHELLSTATE();
            NativeMethods.SHGetSetSettings(ref state, NativeMethods.SSF.SSF_HIDEICONS, false); //get state
            return !state.fHideIcons;
        }

        //ref: https://stackoverflow.com/questions/6402834/how-to-hide-desktop-icons-programmatically/
        public static void SetDesktopIconVisibility(bool isVisible)
        {
            // SHGetSetSettings(ref state, NativeMethods.SSF.SSF_HIDEICONS, true) is not working in Windows 10.
            if (GetDesktopIconVisibility() ^ isVisible)
                NativeMethods.SendMessage(GetDesktopSHELLDLL_DefView(), (int)NativeMethods.WM.COMMAND, (IntPtr)0x7402, IntPtr.Zero);
        }

        /// <summary>
        /// Retrieve Program manager.
        /// </summary>
        public static IntPtr GetProgman()
        {
            return NativeMethods.FindWindow("Progman", null);
        }

        /// <summary>
        /// Retrieves the original WorkerW window that hosts the desktop icons (SHELLDLL_DefView).
        /// </summary>
        public static IntPtr GetDesktopWorkerW()
        {
            var progman = GetProgman();
            var workerWOrig = IntPtr.Zero;
            var folderView = NativeMethods.FindWindowEx(progman, IntPtr.Zero, "SHELLDLL_DefView", null);
            if (folderView == IntPtr.Zero)
            {
                //If the desktop isn't under Progman, cycle through the WorkerW handles and find the correct one
                do
                {
                    workerWOrig = NativeMethods.FindWindowEx(NativeMethods.GetDesktopWindow(), workerWOrig, "WorkerW", null);
                    folderView = NativeMethods.FindWindowEx(workerWOrig, IntPtr.Zero, "SHELLDLL_DefView", null);
                } while (folderView == IntPtr.Zero && workerWOrig != IntPtr.Zero);
            }
            /// Newer versions of Windows 11 (with layered ShellView.)
            return workerWOrig != IntPtr.Zero ? workerWOrig : progman;
        }

        public static IntPtr GetDesktopSHELLDLL_DefView()
        {
            var hShellViewWin = IntPtr.Zero;
            var hWorkerW = IntPtr.Zero;

            var hProgman = NativeMethods.FindWindow("Progman", "Program Manager");
            var hDesktopWnd = NativeMethods.GetDesktopWindow();

            // If the main Program Manager window is found
            if (hProgman != IntPtr.Zero)
            {
                // Get and load the main List view window containing the icons.
                hShellViewWin = NativeMethods.FindWindowEx(hProgman, IntPtr.Zero, "SHELLDLL_DefView", null);
                if (hShellViewWin == IntPtr.Zero)
                {
                    // When this fails (picture rotation is turned ON), then look for the WorkerW windows list to get the
                    // correct desktop list handle.
                    // As there can be multiple WorkerW windows, iterate through all to get the correct one
                    do
                    {
                        hWorkerW = NativeMethods.FindWindowEx(hDesktopWnd, hWorkerW, "WorkerW", null);
                        hShellViewWin = NativeMethods.FindWindowEx(hWorkerW, IntPtr.Zero, "SHELLDLL_DefView", null);
                    } while (hShellViewWin == IntPtr.Zero && hWorkerW != IntPtr.Zero);
                }
            }
            return hShellViewWin;
        }
    }
}
