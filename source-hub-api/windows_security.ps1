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
        $attrs = [IO.File]::GetAttributes($Path)
        $isDirectory = [bool]($attrs -band [IO.FileAttributes]::Directory)
        if (($attrs -band [IO.FileAttributes]::ReparsePoint) -or
            ($isDirectory -ne ($Action -eq 'directory'))) { throw 'unsafe object' }
        if ($isDirectory) { $acl = [IO.Directory]::GetAccessControl($Path) }
        else { $acl = [IO.File]::GetAccessControl($Path) }
        if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -notin $trusted) { throw 'owner' }
        if ($isDirectory -and !$acl.AreAccessRulesProtected) { throw 'inherited directory' }
        $rules = $acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])
        foreach ($rule in $rules) {
            if ($rule.IdentityReference.Value -notin $trusted -or $rule.AccessControlType -ne 'Allow' -or
                $rule.FileSystemRights -ne 'FullControl' -or
                ($isDirectory -and ($rule.IsInherited -or
                 $rule.InheritanceFlags -ne 'ContainerInherit,ObjectInherit' -or
                 $rule.PropagationFlags -ne 'None'))) { throw 'unexpected rule' }
        }
        if ($rules.Count -ne 2 -or $rules[0].IdentityReference.Value -eq $rules[1].IdentityReference.Value) {
            throw 'missing access rules'
        }
    } elseif ($Action -in @('protect','unprotect')) {
        [void][Reflection.Assembly]::Load('System.Security, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b03f5f7f11d50a3a')
        $scope = [Security.Cryptography.DataProtectionScope]::CurrentUser
        if ($Action -eq 'protect') {
            $bytes = [Text.Encoding]::ASCII.GetBytes([Console]::In.ReadToEnd())
            try {
                $encrypted = [Security.Cryptography.ProtectedData]::Protect($bytes,$null,$scope)
                [Console]::Out.Write([Convert]::ToBase64String($encrypted))
            } finally { [Array]::Clear($bytes,0,$bytes.Length) }
        } else {
            $encrypted = [Convert]::FromBase64String([Console]::In.ReadToEnd())
            $bytes = [Security.Cryptography.ProtectedData]::Unprotect($encrypted,$null,$scope)
            try { [Console]::Out.Write([Text.Encoding]::ASCII.GetString($bytes)) }
            finally { [Array]::Clear($bytes,0,$bytes.Length) }
        }
    }
} catch {
    $reason = $_.Exception.Message
    if ($Action -in @('create','directory','file')) {
        if ($reason -in @('local NTFS required','unsafe object','owner','inherited directory','unexpected rule','missing access rules')) {
            [Console]::Error.WriteLine($reason)
        } else {
            [Console]::Error.WriteLine($_.Exception.GetType().Name)
        }
    }
    exit 1
}
