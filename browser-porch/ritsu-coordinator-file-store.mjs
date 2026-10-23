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
