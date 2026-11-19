package edu.whpu.reagent.persistence.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import edu.whpu.reagent.domain.Reagent;
import edu.whpu.reagent.persistence.ReagentListRow;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface ReagentMapper extends BaseMapper<Reagent> {

    List<ReagentListRow> listRows();

    Reagent findPending(@Param("slot") int slot);

    Reagent findByChip(@Param("uid") String uid);

    int insertReagent(Reagent reagent);

    int updateReagent(Reagent reagent);

    int deleteReagent(@Param("id") long id);
}
