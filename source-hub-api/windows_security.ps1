param([ValidateSet('create','directory','file','protect','unprotect')][string]$Action,[string]$Path)
$ErrorActionPreference = 'Stop'
try {
    $drive = [IO.DriveInfo]::new([IO.Path]::GetPathRoot($Path))
    if ($drive.DriveType -ne 'Fixed' -or $drive.DriveFormat -ne 'NTFS') { throw 'local NTFS required' }
    $user = [Security.Principal.WindowsIdentity]::GetCurrent().User
    $system = [Security.Principal.SecurityIdentifier]::new('S-1-5-18')
    $trusted = @($user.Value,$system.Value)
    if ($Action -eq 'create') {
        $acl = [Security.AccessControl.DirectorySecurity]::new()
        $acl.SetOwner($user)
        $acl.SetAccessRuleProtection($true,$false)
        foreach ($sid in @($user,$system)) {
            $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new(
                $sid,'FullControl','ContainerInherit,ObjectInherit','None','Allow'))
        }
        [void][IO.Directory]::CreateDirectory($Path,$acl)
        $Action = 'directory'
    }
    if ($Action -in @('directory','file')) {
        $item = Get-Item -LiteralPath $Path -Force
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
            ($item.PSIsContainer -ne ($Action -eq 'directory'))) { throw 'unsafe object' }
        $acl = Get-Acl -LiteralPath $Path
        if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin $trusted) { throw 'owner' }
        if ($Action -eq 'directory' -and !$acl.AreAccessRulesProtected) { throw 'inherited directory' }
        $rules = @($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]))
        foreach ($rule in $rules) {
            if ($rule.IdentityReference.Value -notin $trusted -or $rule.AccessControlType -ne 'Allow' -or
                $rule.FileSystemRights -ne 'FullControl' -or
                ($Action -eq 'directory' -and ($rule.IsInherited -or
                 $rule.InheritanceFlags -ne 'ContainerInherit,ObjectInherit' -or
                 $rule.PropagationFlags -ne 'None'))) { throw 'unexpected rule' }
        }
        if ($rules.Count -ne 2 -or @($rules | ForEach-Object {$_.IdentityReference.Value} |
                Select-Object -Unique).Count -ne 2) { throw 'missing access rules' }
    } elseif ($Action -eq 'protect') {
        $secure = ConvertTo-SecureString ([Console]::In.ReadToEnd()) -AsPlainText -Force
        try { [Console]::Out.Write((ConvertFrom-SecureString $secure)) } finally {$secure.Dispose()}
    } elseif ($Action -eq 'unprotect') {
        $secure = ConvertTo-SecureString ([Console]::In.ReadToEnd())
        $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
        try { [Console]::Out.Write([Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)) }
        finally {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
            $secure.Dispose()
        }
    }
} catch {
    [Console]::Error.WriteLine('Windows private security operation failed.')
    exit 1
}
