// Local durable adapter for a single Home Center coordinator process.
// File state is atomic within one instance; production multi-process writers
// require a shared transactional datastore with compare-and-swap/leases.
import {mkdir,readFile,open,rename,rm} from 'node:fs/promises';
import {randomUUID,createHash} from 'node:crypto';
import path from 'node:path';

export function createFileCoordinatorStore({directory}={}) {
  if (!directory || !path.isAbsolute(directory))
    throw new Error('absolute_home_center_private_directory_required');
  const namespacePath=(key)=>{
    if (!/^[A-Za-z0-9_.:-]{8,100}$/.test(String(key||'')))
      throw new Error('invalid_state_namespace');
    return path.join(directory,
      createHash('sha256').update(key).digest('hex')+'.json');
  };
  return Object.freeze({
    // Each CLI invocation creates its own coordinator instance. Serialize
    // read/modify/write across independent processes with O_EXCL lock files.
    // A crashed holder leaves a lock that fails closed, rather than risking
    // duplicate browser sends or a lost deterministic merge.
    async withNamespaceLock(namespace, work) {
      const lockFile=namespacePath(namespace)+'.lock';
      await mkdir(directory,{recursive:true,mode:0o700});
      let handle=null;
      const end=Date.now()+8000;
      while (!handle) {
        try { handle=await open(lockFile,'wx',0o600); }
        catch (error) {
          if (error.code !== 'EEXIST' || Date.now()>=end)
            throw new Error(error.code==='EEXIST'
              ? 'coordinator_locked_manual_recovery_required'
              : 'coordinator_lock_acquisition_failed');
          await new Promise(resolve=>setTimeout(resolve,50));
        }
      }
      try {
        await handle.writeFile(JSON.stringify({pid:process.pid,at:new Date().toISOString()}));
        await handle.sync();
        return await work();
      } finally {
        try {await handle.close();} finally {await rm(lockFile,{force:true});}
      }
    },
    async load(namespace) {
      const file=namespacePath(namespace);
      try {return JSON.parse(await readFile(file,'utf8'));}
      catch(error) {
        if(error.code==='ENOENT')return null;
        throw error; // corruption is NOT equivalent to new/empty session
      }
    },
    async save(namespace,state) {
      const file=namespacePath(namespace);
      await mkdir(directory,{recursive:true,mode:0o700});
      const temporary=file+'.'+randomUUID()+'.tmp';
      try {
        const handle=await open(temporary,'wx',0o600);
        try {
          await handle.writeFile(JSON.stringify(state),'utf8');
          await handle.sync();
        } finally {await handle.close();}
        await rename(temporary,file);
        // On platforms permitting directory fsync, make rename durable too.
        try {
          const dir=await open(directory,'r');
          try {await dir.sync();} finally {await dir.close();}
        } catch(error) {
          if (!['EINVAL','EPERM','EISDIR','EBADF','ENOTSUP'].includes(error.code))
            throw error;
        }
      } finally {await rm(temporary,{force:true}).catch(()=>{});}
    },
  });
}
